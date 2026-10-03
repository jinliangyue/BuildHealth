"""
Audit log · middleware + router
================================
Phase 7 tests. Verifies that:

  - the middleware writes one row per non-exempt HTTP request
  - exempt paths (/api/health, /docs, /redoc, /openapi.json) are skipped
  - the row captures method / path / status / duration / request_id
  - /api/audit lists rows newest-first and supports pagination
  - /api/audit/stats returns aggregate counts and a top-paths table
  - the response carries an `x-request-id` header
  - audit failures never propagate as 500s to the caller
"""
import time

from sqlalchemy import select, func

from app.db import models


# --------------------------------------------------------------------- helpers
def _all_audit_rows(test_session):
    return test_session.execute(
        select(models.AuditLog).order_by(models.AuditLog.timestamp)
    ).scalars().all()


# --------------------------------------------------------------------- middleware
def test_audit_records_real_request(client, test_session):
    """A non-exempt GET produces exactly one audit row with the expected fields."""
    response = client.get("/")
    assert response.status_code == 200
    # x-request-id is exposed on the response
    assert "x-request-id" in response.headers

    rows = _all_audit_rows(test_session)
    assert len(rows) == 1
    row = rows[0]
    assert row.method == "GET"
    assert row.path == "/"
    assert row.status_code == 200
    assert row.duration_ms >= 0
    assert row.request_id == response.headers["x-request-id"]
    # No request/response body content is stored
    assert not hasattr(row, "body") or getattr(row, "body", None) is None


def test_audit_skips_exempt_paths(client, test_session):
    """Health, docs, openapi.json and audit endpoints must not pollute the audit table."""
    for path in ("/api/health", "/docs", "/redoc", "/openapi.json", "/favicon.ico"):
        response = client.get(path)
        # 200 for the live endpoints, 404 for favicon; either way, no
        # audit row should be written.
        assert response.status_code in (200, 404)

    rows = _all_audit_rows(test_session)
    assert rows == [], f"Expected no audit rows for exempt paths, got: {[r.path for r in rows]}"


def test_audit_records_method_and_path_for_each_request(client, test_session):
    """Multiple requests produce one row each, newest timestamp ordering respected."""
    client.get("/api/health")            # exempt → no row
    client.get("/")
    client.get("/")
    client.get("/docs")                  # exempt → no row

    rows = _all_audit_rows(test_session)
    assert len(rows) == 2
    # Both non-exempt rows are for path "/"
    assert {r.path for r in rows} == {"/"}
    assert {r.method for r in rows} == {"GET"}


def test_audit_records_404_as_well_as_2xx(client, test_session):
    """Audit captures the real status code, even when the request was unsuccessful."""
    client.get("/this-endpoint-does-not-exist")
    rows = _all_audit_rows(test_session)
    assert len(rows) == 1
    assert rows[0].status_code == 404
    assert rows[0].path == "/this-endpoint-does-not-exist"


def test_audit_does_not_break_on_long_user_agent(client, test_session):
    """Adversarially long User-Agent must not crash the request."""
    long_ua = "x" * 1024
    response = client.get("/", headers={"user-agent": long_ua})
    assert response.status_code == 200

    rows = _all_audit_rows(test_session)
    assert len(rows) == 1
    # UA was truncated, never stored in full
    assert len(rows[0].user_agent) == 256


def test_audit_write_failure_does_not_break_request(client, test_session, monkeypatch):
    """If the audit INSERT raises, the request still returns successfully."""

    from app.audit import middleware as mw_module

    def broken_factory():
        def _raise():
            raise RuntimeError("simulated audit-table outage")
        return _raise()

    # Replace the factory on app.state for this test only
    original = getattr(client.app.state, "audit_session_factory", None)
    client.app.state.audit_session_factory = broken_factory
    try:
        # Request should still return 200; middleware swallows the error
        response = client.get("/")
        assert response.status_code == 200
    finally:
        client.app.state.audit_session_factory = original


def test_audit_x_request_id_is_unique_per_request(client, test_session):
    """Every non-exempt request gets a fresh UUID4."""
    ids = set()
    for _ in range(5):
        response = client.get("/")
        rid = response.headers.get("x-request-id")
        assert rid is not None
        assert rid not in ids
        ids.add(rid)
    assert len(ids) == 5


# --------------------------------------------------------------------- router
def test_audit_endpoint_returns_rows_newest_first(client, test_session):
    for path in ("/", "/", "/"):
        client.get(path)

    response = client.get("/api/audit")
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 3
    assert payload["limit"] == 50
    assert payload["offset"] == 0
    assert len(payload["items"]) == 3
    # Newest-first: timestamps must be monotonically non-increasing
    timestamps = [item["timestamp"] for item in payload["items"]]
    assert timestamps == sorted(timestamps, reverse=True)


def test_audit_endpoint_pagination(client, test_session):
    for _ in range(5):
        client.get("/")

    page1 = client.get("/api/audit?limit=2&offset=0").json()
    page2 = client.get("/api/audit?limit=2&offset=2").json()
    page3 = client.get("/api/audit?limit=2&offset=4").json()

    assert page1["total"] == 5
    assert page2["total"] == 5
    assert page3["total"] == 5

    assert len(page1["items"]) == 2
    assert len(page2["items"]) == 2
    assert len(page3["items"]) == 1

    # Pages must not overlap
    ids1 = {i["id"] for i in page1["items"]}
    ids2 = {i["id"] for i in page2["items"]}
    ids3 = {i["id"] for i in page3["items"]}
    assert ids1.isdisjoint(ids2)
    assert ids1.isdisjoint(ids3)
    assert ids2.isdisjoint(ids3)


def test_audit_endpoint_method_filter(client, test_session):
    # Two GETs and (we'll attempt) one POST. POST hits a path that
    # doesn't exist → 404, but the audit row is still GET vs POST.
    client.get("/")
    client.get("/")
    client.post("/")

    only_get = client.get("/api/audit?method=GET").json()
    only_post = client.get("/api/audit?method=POST").json()

    assert only_get["total"] == 2
    assert only_post["total"] == 1
    assert all(item["method"] == "GET" for item in only_get["items"])
    assert all(item["method"] == "POST" for item in only_post["items"])


def test_audit_endpoint_status_min_filter(client, test_session):
    client.get("/")                       # 200
    client.get("/missing-route")          # 404
    client.get("/missing-again")          # 404

    only_4xx_5xx = client.get("/api/audit?status_min=400").json()
    assert only_4xx_5xx["total"] == 2
    assert all(item["status_code"] >= 400 for item in only_4xx_5xx["items"])


def test_audit_stats_endpoint(client, test_session):
    client.get("/")              # 200
    client.get("/")
    client.get("/missing")       # 404
    client.get("/missing-again")  # 404
    client.get("/missing-3rd")    # 404

    response = client.get("/api/audit/stats?hours=1")
    assert response.status_code == 200
    stats = response.json()
    assert stats["total_requests"] == 5
    assert stats["error_count"] == 0  # 4xx is not 5xx
    assert stats["avg_duration_ms"] >= 0
    assert any(p["path"] == "/" for p in stats["top_paths"])
    # Top paths sorted descending by count
    counts = [p["count"] for p in stats["top_paths"]]
    assert counts == sorted(counts, reverse=True)


def test_audit_stats_window_hours_validation(client):
    """hours parameter has bounds; out-of-range must return 422."""
    assert client.get("/api/audit/stats?hours=0").status_code == 422
    assert client.get("/api/audit/stats?hours=169").status_code == 422
    assert client.get("/api/audit/stats?hours=24").status_code == 200


def test_audit_endpoint_does_not_count_exempt_paths(client, test_session):
    """End-to-end: only real requests show up in /api/audit."""
    for _ in range(3):
        client.get("/api/health")   # exempt
    client.get("/")                 # non-exempt

    response = client.get("/api/audit")     # also exempt (introspection)
    payload = response.json()
    assert payload["total"] == 1


def test_audit_endpoint_does_not_audit_itself(client, test_session):
    """Hitting /api/audit must not add a row, otherwise introspection
    pollutes the table unboundedly."""
    for _ in range(3):
        client.get("/api/audit")
        client.get("/api/audit/stats")
    client.get("/")  # the only row that should exist
    rows = _all_audit_rows(test_session)
    assert len(rows) == 1
    assert rows[0].path == "/"
