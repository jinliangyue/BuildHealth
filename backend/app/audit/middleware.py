"""
Audit middleware · BuildHealth Phase 7
======================================

Writes one `audit_logs` row per HTTP request. The middleware is
intentionally minimal:

  - Body is never read or stored. We only record method, path, status,
    duration, client IP (truncated), user agent (truncated) and a
    per-request UUID4 for cross-referencing with structured logs.
  - The DB write is synchronous but wrapped in try/except so a transient
    audit-table failure can never propagate as a 500 to the caller. The
    application is decoupled from its own audit trail by design.
  - Health check and OpenAPI docs paths are exempt (`/api/health`,
    `/docs`, `/redoc`, `/openapi.json`) so the table is not flooded by
    load-balancer probes.

Path strings and query strings are truncated at module level to keep
the schema bounded against adversarial or accidental long URLs.
"""
from __future__ import annotations

import logging
import time
import uuid
from typing import Awaitable, Callable, Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import SessionLocal

logger = logging.getLogger("buildhealth.audit")

# Paths that should not generate audit rows. Exempt because:
#   - /api/health:    load-balancer probes, would dominate the table
#   - /docs, /redoc:  Swagger UI assets
#   - /openapi.json:  generated per-request; the schema, not usage
#   - /api/audit*:    introspection of the audit log itself; auditing
#                     these would create unbounded recursive growth and
#                     pollute the table with operator queries
EXEMPT_PATHS = frozenset({
    "/api/health",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/favicon.ico",
    "/api/audit",
    "/api/audit/stats",
})

# Bounds from models.AuditLog column widths
MAX_PATH_LEN = 512
MAX_QUERY_LEN = 512
MAX_UA_LEN = 256
# IPv4 textual length ≤ 15, IPv6 textual length ≤ 39; 64 covers both
# plus any IPv6-mapped prefix we might keep.
MAX_IP_LEN = 64


def _truncate(value: Optional[str], limit: int) -> Optional[str]:
    if value is None:
        return None
    if len(value) <= limit:
        return value
    return value[:limit]


def _extract_client_ip(request: Request) -> str:
    """Return the best-effort client IP.

    Honors X-Forwarded-For when present (first hop only), falling back
    to the direct client. We do not trust the header for security
    decisions; this is just an audit hint.
    """
    xff = request.headers.get("x-forwarded-for")
    if xff:
        # First entry in the comma-separated list
        first = xff.split(",", 1)[0].strip()
        if first:
            return _truncate(first, MAX_IP_LEN) or "unknown"
    if request.client and request.client.host:
        return _truncate(request.client.host, MAX_IP_LEN) or "unknown"
    return "unknown"


class AuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        path = request.url.path
        if path in EXEMPT_PATHS:
            return await call_next(request)

        # Generate request_id once; expose on response so callers can
        # cross-reference their access log with our audit row.
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        # Allow tests (and any future production override) to swap the
        # session factory used by the audit write. Production code uses
        # the default SessionLocal bound to the real engine.
        session_factory = getattr(
            request.app.state,
            "audit_session_factory",
            None,
        )
        if session_factory is None:
            session_factory = SessionLocal

        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            # call_next propagates by re-raising; still record the
            # 500-equivalent row below before letting it bubble.
            duration_ms = (time.perf_counter() - started) * 1000.0
            self._safe_write(
                session_factory=session_factory,
                method=request.method,
                path=path,
                query_string=_truncate(request.url.query, MAX_QUERY_LEN),
                status_code=500,
                duration_ms=duration_ms,
                client_ip=_extract_client_ip(request),
                user_agent=_truncate(
                    request.headers.get("user-agent"), MAX_UA_LEN
                ),
                request_id=request_id,
            )
            raise

        duration_ms = (time.perf_counter() - started) * 1000.0
        self._safe_write(
            session_factory=session_factory,
            method=request.method,
            path=path,
            query_string=_truncate(request.url.query, MAX_QUERY_LEN),
            status_code=response.status_code,
            duration_ms=duration_ms,
            client_ip=_extract_client_ip(request),
            user_agent=_truncate(
                request.headers.get("user-agent"), MAX_UA_LEN
            ),
            request_id=request_id,
        )
        # Surface the request_id for any downstream logging the
        # application chooses to do.
        response.headers["x-request-id"] = request_id
        return response

    @staticmethod
    def _safe_write(
        *,
        session_factory,
        method: str,
        path: str,
        query_string: Optional[str],
        status_code: int,
        duration_ms: float,
        client_ip: str,
        user_agent: Optional[str],
        request_id: str,
    ) -> None:
        """Persist one audit row; never raise.

        The audit log must not become a failure surface for the API.
        Any DB exception is logged at WARNING and swallowed.
        """
        try:
            # Import lazily so the middleware can be imported without
            # triggering the whole models module at startup.
            from app.db.models import AuditLog

            session = session_factory()
            try:
                row = AuditLog(
                    method=method[:8],
                    path=_truncate(path, MAX_PATH_LEN) or "/",
                    query_string=query_string,
                    status_code=status_code,
                    duration_ms=round(duration_ms, 3),
                    client_ip=client_ip,
                    user_agent=user_agent,
                    request_id=request_id,
                )
                session.add(row)
                session.commit()
            finally:
                session.close()
        except SQLAlchemyError as exc:
            logger.warning(
                "audit write failed: %s (method=%s path=%s status=%s)",
                exc.__class__.__name__, method, path, status_code,
            )
        except Exception as exc:  # pragma: no cover  (defensive)
            logger.warning(
                "audit write unexpected error: %s", exc,
            )
