from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable, Mapping
from urllib.error import HTTPError
from urllib.parse import quote, urlencode, urljoin
from urllib.request import Request, urlopen

from .errors import AgentBoxApiError

JsonMapping = Mapping[str, Any]


@dataclass(frozen=True)
class AgentBoxHttpResponse:
    status: int
    reason: str
    body: bytes


Transport = Callable[[str, str, Mapping[str, str], bytes | None, float | None], AgentBoxHttpResponse]


class AgentBoxClient:
    def __init__(
        self,
        *,
        base_url: str,
        actor: str | None = None,
        token: str | None = None,
        identity_token: str | None = None,
        grant_token: str | None = None,
        auth_scheme: str | None = None,
        transport: Transport | None = None,
        timeout: float | None = None,
    ) -> None:
        actor = _optional_non_empty(actor)
        token = _optional_non_empty(token)
        identity_token = _optional_non_empty(identity_token)
        grant_token = _optional_non_empty(grant_token)
        auth_scheme = _optional_non_empty(auth_scheme)

        if token and identity_token:
            raise TypeError("AgentBoxClient token and identity_token auth modes are mutually exclusive.")
        if not token and not identity_token:
            raise TypeError("AgentBoxClient requires a token or identity_token.")
        if token and not actor:
            raise TypeError("AgentBoxClient requires a non-empty actor when using token auth.")

        self._base_url = _ensure_trailing_slash(base_url)
        self._actor = actor
        self._token = token
        self._identity_token = identity_token
        self._grant_token = grant_token
        self._auth_scheme = auth_scheme
        self._transport = transport or _urllib_transport
        self._timeout = timeout

    def health(self) -> dict[str, Any]:
        return self._request("GET", "/health", auth=False)

    def register_agent(self, data: JsonMapping | None = None, **options: Any) -> dict[str, Any]:
        return self._request("POST", "/v1/agents/register", body=dict(data or {}), options=options)

    def get_agent_profile(self, **options: Any) -> dict[str, Any]:
        return self._request("GET", "/v1/agents/me", options=options)

    def list_agents(self, **options: Any) -> dict[str, Any]:
        return self._request("GET", "/v1/agents", options=options)

    def update_agent_status(self, data: JsonMapping, **options: Any) -> dict[str, Any]:
        body = {key: value for key, value in data.items() if key != "identity_key"}
        return self._request(
            "PATCH",
            f"/v1/agents/{_path_segment(data['identity_key'])}/status",
            body=body,
            options=options,
        )

    def create_box(self, data: JsonMapping, **options: Any) -> dict[str, Any]:
        return self._request("POST", "/v1/boxes", body=data, options=options)

    def list_boxes(self, **options: Any) -> dict[str, Any]:
        return self._request("GET", "/v1/boxes", options=options)

    def get_manifest(self, data: JsonMapping, **options: Any) -> dict[str, Any]:
        return self._request("GET", f"/v1/boxes/{_path_segment(data['box_id'])}/manifest", options=options)

    def put_item(self, data: JsonMapping, **options: Any) -> dict[str, Any]:
        body = {key: value for key, value in data.items() if key not in {"box_id", "key"}}
        return self._request(
            "PUT",
            f"/v1/boxes/{_path_segment(data['box_id'])}/items/{_key_path(data['key'])}",
            body=body,
            options=options,
        )

    def get_item(self, data: JsonMapping, **options: Any) -> dict[str, Any]:
        query: dict[str, Any] = {}
        if "version" in data and data["version"] is not None:
            query["version"] = data["version"]
        return self._request(
            "GET",
            f"/v1/boxes/{_path_segment(data['box_id'])}/items/{_key_path(data['key'])}",
            query=query,
            options=options,
        )

    def list_items(self, data: JsonMapping, **options: Any) -> dict[str, Any]:
        query: dict[str, Any] = {}
        if data.get("prefix"):
            query["prefix"] = data["prefix"]
        if data.get("content_type"):
            query["content_type"] = data["content_type"]
        if data.get("tags"):
            query["tags"] = ",".join(data["tags"])
        return self._request("GET", f"/v1/boxes/{_path_segment(data['box_id'])}/items", query=query, options=options)

    def append_event(self, data: JsonMapping, **options: Any) -> dict[str, Any]:
        body = {key: value for key, value in data.items() if key not in {"box_id", "stream"}}
        return self._request(
            "POST",
            f"/v1/boxes/{_path_segment(data['box_id'])}/events/{_path_segment(data['stream'])}",
            body=body,
            options=options,
        )

    def list_events(self, data: JsonMapping, **options: Any) -> dict[str, Any]:
        query: dict[str, Any] = {}
        if "after_seq" in data and data["after_seq"] is not None:
            query["after_seq"] = data["after_seq"]
        if "limit" in data and data["limit"] is not None:
            query["limit"] = data["limit"]
        return self._request(
            "GET",
            f"/v1/boxes/{_path_segment(data['box_id'])}/events/{_path_segment(data['stream'])}",
            query=query,
            options=options,
        )

    def attach_artifact(self, data: JsonMapping, **options: Any) -> dict[str, Any]:
        body = {key: value for key, value in data.items() if key != "box_id"}
        return self._request("POST", f"/v1/boxes/{_path_segment(data['box_id'])}/artifacts", body=body, options=options)

    def list_artifacts(self, data: JsonMapping, **options: Any) -> dict[str, Any]:
        return self._request("GET", f"/v1/boxes/{_path_segment(data['box_id'])}/artifacts", options=options)

    def get_artifact(self, data: JsonMapping, **options: Any) -> dict[str, Any]:
        return self._request(
            "GET",
            f"/v1/boxes/{_path_segment(data['box_id'])}/artifacts/{_path_segment(data['artifact_id'])}",
            options=options,
        )

    def create_grant(self, data: JsonMapping, **options: Any) -> dict[str, Any]:
        body = {key: value for key, value in data.items() if key != "box_id"}
        return self._request("POST", f"/v1/boxes/{_path_segment(data['box_id'])}/grants", body=body, options=options)

    def list_grants(self, data: JsonMapping, **options: Any) -> dict[str, Any]:
        return self._request("GET", f"/v1/boxes/{_path_segment(data['box_id'])}/grants", options=options)

    def revoke_grant(self, data: JsonMapping, **options: Any) -> dict[str, Any]:
        return self._request(
            "POST",
            f"/v1/boxes/{_path_segment(data['box_id'])}/grants/{_path_segment(data['grant_id'])}/revoke",
            body={},
            options=options,
        )

    def list_audit(self, data: JsonMapping, **options: Any) -> dict[str, Any]:
        return self._request("GET", f"/v1/boxes/{_path_segment(data['box_id'])}/audit", options=options)

    def with_auth(
        self,
        *,
        actor: str | None = None,
        token: str | None = None,
        identity_token: str | None = None,
        grant_token: str | None = None,
        auth_scheme: str | None = None,
    ) -> "AgentBoxClient":
        token = _optional_non_empty(token)
        identity_token = _optional_non_empty(identity_token)
        grant_token = _optional_non_empty(grant_token)
        auth_scheme = _optional_non_empty(auth_scheme)

        if token and identity_token:
            raise TypeError("AgentBoxClient token and identity_token auth modes are mutually exclusive.")

        if identity_token:
            next_actor = _optional_non_empty(actor) or (self._actor if self._identity_token else None)
            return AgentBoxClient(
                base_url=self._base_url,
                actor=next_actor,
                identity_token=identity_token,
                grant_token=grant_token,
                auth_scheme=auth_scheme or (self._auth_scheme if self._identity_token else None),
                transport=self._transport,
                timeout=self._timeout,
            )

        if token:
            next_actor = _optional_non_empty(actor) or (self._actor if self._token else None)
            return AgentBoxClient(
                base_url=self._base_url,
                actor=next_actor,
                token=token,
                grant_token=grant_token,
                auth_scheme=auth_scheme or (self._auth_scheme if self._token else None),
                transport=self._transport,
                timeout=self._timeout,
            )

        return AgentBoxClient(
            base_url=self._base_url,
            actor=_optional_non_empty(actor) or self._actor,
            token=self._token,
            identity_token=self._identity_token,
            grant_token=grant_token or self._grant_token,
            auth_scheme=auth_scheme or self._auth_scheme,
            transport=self._transport,
            timeout=self._timeout,
        )

    def _request(
        self,
        method: str,
        path: str,
        *,
        query: Mapping[str, Any] | None = None,
        body: JsonMapping | None = None,
        auth: bool = True,
        options: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        url = urljoin(self._base_url, path.lstrip("/"))
        if query:
            url = f"{url}?{urlencode({key: str(value) for key, value in query.items()})}"

        headers = {"accept": "application/json"}
        request_body = None
        if body is not None:
            headers["content-type"] = "application/json"
            request_body = json.dumps(body, separators=(",", ":")).encode("utf-8")

        if auth:
            resolved = self._resolve_auth(options or {})
            headers["authorization"] = f"Bearer {resolved['authorization_token']}"
            if resolved.get("actor"):
                headers["x-agentbox-actor"] = resolved["actor"]
            if resolved.get("grant_token"):
                headers["x-agentbox-grant-token"] = resolved["grant_token"]
            if resolved.get("auth_scheme"):
                headers["x-agentbox-auth-scheme"] = resolved["auth_scheme"]
            if resolved.get("admin"):
                headers["x-agentbox-admin"] = "true"

        response = self._transport(method, url, headers, request_body, self._timeout)
        payload = _parse_json_response(response)

        if response.status < 200 or response.status >= 300 or not _is_success_payload(payload):
            error_payload = payload if _is_error_payload(payload) else _fallback_error_payload(response)
            error = error_payload["error"]
            raise AgentBoxApiError(
                code=error["code"],
                message=error["message"],
                target=error.get("target"),
                request_id=error.get("request_id"),
                audit_id=error_payload.get("audit_id"),
                status=response.status,
            )

        return payload

    def _resolve_auth(self, options: Mapping[str, Any]) -> dict[str, Any]:
        option_identity_token = _optional_non_empty(options.get("identity_token"))
        option_token = _optional_non_empty(options.get("token"))
        if option_identity_token and option_token:
            raise TypeError("AgentBoxClient token and identity_token auth modes are mutually exclusive.")

        identity_token = option_identity_token or (None if option_token else self._identity_token)
        token = option_token or (None if option_identity_token else self._token)
        grant_token = _optional_non_empty(options.get("grant_token")) or self._grant_token
        switches_auth_mode = bool((option_identity_token and not self._identity_token) or (option_token and not self._token))
        actor = _optional_non_empty(options.get("actor")) if switches_auth_mode else _optional_non_empty(options.get("actor")) or self._actor
        auth_scheme = _optional_non_empty(options.get("auth_scheme")) or (None if switches_auth_mode else self._auth_scheme)

        if identity_token:
            return {
                "authorization_token": identity_token,
                "actor": actor,
                "grant_token": grant_token,
                "auth_scheme": auth_scheme,
                "admin": options.get("admin"),
            }

        if not token:
            raise TypeError("AgentBoxClient request requires a token or identity_token.")
        if not actor:
            raise TypeError("AgentBoxClient request requires an actor when using token auth.")

        return {
            "authorization_token": token,
            "actor": actor,
            "grant_token": grant_token,
            "auth_scheme": auth_scheme,
            "admin": options.get("admin"),
        }


def _urllib_transport(
    method: str,
    url: str,
    headers: Mapping[str, str],
    body: bytes | None,
    timeout: float | None,
) -> AgentBoxHttpResponse:
    request = Request(url, data=body, headers=dict(headers), method=method)
    try:
        with urlopen(request, timeout=timeout) as response:
            return AgentBoxHttpResponse(response.status, response.reason, response.read())
    except HTTPError as error:
        return AgentBoxHttpResponse(error.code, error.reason, error.read())


def _parse_json_response(response: AgentBoxHttpResponse) -> Any:
    if not response.body:
        return None
    try:
        return json.loads(response.body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise AgentBoxApiError(
            code="invalid_response",
            message="AgentBox returned a non-JSON response.",
            status=response.status,
        ) from error


def _is_success_payload(value: Any) -> bool:
    return isinstance(value, dict) and value.get("ok") is True and "data" in value and value.get("error") is None


def _is_error_payload(value: Any) -> bool:
    return (
        isinstance(value, dict)
        and value.get("ok") is False
        and isinstance(value.get("error"), dict)
        and isinstance(value["error"].get("code"), str)
        and isinstance(value["error"].get("message"), str)
    )


def _fallback_error_payload(response: AgentBoxHttpResponse) -> dict[str, Any]:
    return {
        "ok": False,
        "data": None,
        "error": {
            "code": "http_error",
            "message": response.reason or f"HTTP {response.status}",
        },
        "audit_id": None,
    }


def _ensure_trailing_slash(value: str) -> str:
    return value if value.endswith("/") else f"{value}/"


def _path_segment(value: Any) -> str:
    return quote(str(value), safe="")


def _key_path(value: Any) -> str:
    return "/".join(_path_segment(part) for part in str(value).split("/"))


def _optional_non_empty(value: Any) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None
