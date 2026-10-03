"""
Audit module · BuildHealth Phase 7
==================================

Persistence and inspection of access logs.

- middleware: writes one row per HTTP request (fire-and-forget; never
  raises into the request lifecycle)
- router: GET /api/audit (paginated) and GET /api/audit/stats (summary)
- schemas: Pydantic shapes for the response payloads

This module deliberately does not record request/response bodies. The
audit log captures *access behaviour* ("who hit what when"), not
content. See `models.AuditLog` docstring for the rationale.
"""
