from __future__ import annotations


class AgentBoxApiError(Exception):
    """Structured error returned by the AgentBox REST API."""

    def __init__(
        self,
        *,
        code: str,
        message: str,
        status: int,
        target: str | None = None,
        request_id: str | None = None,
        audit_id: str | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.status = status
        self.target = target
        self.request_id = request_id
        self.audit_id = audit_id
