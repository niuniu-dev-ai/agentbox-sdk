from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Mapping
from urllib.parse import urljoin, urlparse, urlunparse

from .client import (
    AgentBoxClient,
    AgentBoxHttpResponse,
    Transport,
    _ensure_trailing_slash,
    _optional_non_empty,
    _urllib_transport,
)
from .errors import AgentBoxApiError


@dataclass(frozen=True)
class AgentBoxDiscovery:
    agent_card_url: str
    base_url: str
    a2a_url: str
    rest_api_base_url: str
    name: str | None
    description: str | None
    security_schemes: Mapping[str, Any]
    agent_card: Mapping[str, Any]
    transport: Transport | None = None
    timeout: float | None = None

    def create_client(
        self,
        *,
        actor: str | None = None,
        token: str | None = None,
        identity_token: str | None = None,
        grant_token: str | None = None,
        auth_scheme: str | None = None,
        transport: Transport | None = None,
        timeout: float | None = None,
    ) -> AgentBoxClient:
        return AgentBoxClient(
            base_url=self.base_url,
            actor=actor,
            token=token,
            identity_token=identity_token,
            grant_token=grant_token,
            auth_scheme=auth_scheme,
            transport=transport or self.transport,
            timeout=self.timeout if timeout is None else timeout,
        )


def discover_agentbox(
    *,
    base_url: str | None = None,
    agent_card_url: str | None = None,
    transport: Transport | None = None,
    timeout: float | None = None,
) -> AgentBoxDiscovery:
    resolved_card_url = _resolve_agent_card_url(base_url=base_url, agent_card_url=agent_card_url)
    run_transport = transport or _urllib_transport
    response = run_transport("GET", resolved_card_url, {"accept": "application/json"}, None, timeout)
    payload = _parse_agent_card_response(response)
    if not isinstance(payload, dict) or not _optional_non_empty(payload.get("url")):
        raise AgentBoxApiError(
            code="invalid_response",
            message="AgentBox discovery response did not include a valid Agent Card.",
            status=response.status,
        )

    resolved_base_url = _base_url_from_card(payload, resolved_card_url)
    security_schemes = payload.get("securitySchemes")

    return AgentBoxDiscovery(
        agent_card_url=resolved_card_url,
        base_url=resolved_base_url,
        a2a_url=str(payload["url"]),
        rest_api_base_url=urljoin(_ensure_trailing_slash(resolved_base_url), "v1"),
        name=_optional_non_empty(payload.get("name")),
        description=_optional_non_empty(payload.get("description")),
        security_schemes=security_schemes if isinstance(security_schemes, dict) else {},
        agent_card=payload,
        transport=transport,
        timeout=timeout,
    )


def _resolve_agent_card_url(*, base_url: str | None, agent_card_url: str | None) -> str:
    normalized_card_url = _optional_non_empty(agent_card_url)
    normalized_base_url = _optional_non_empty(base_url)
    if normalized_card_url:
        return normalized_card_url
    if normalized_base_url:
        return urljoin(_ensure_trailing_slash(normalized_base_url), ".well-known/agent-card.json")
    raise TypeError("discover_agentbox requires base_url or agent_card_url.")


def _parse_agent_card_response(response: AgentBoxHttpResponse) -> Any:
    if response.status < 200 or response.status >= 300:
        raise AgentBoxApiError(
            code="http_error",
            message=response.reason or f"HTTP {response.status}",
            status=response.status,
        )
    try:
        return json.loads(response.body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise AgentBoxApiError(
            code="invalid_response",
            message="AgentBox discovery returned a non-JSON response.",
            status=response.status,
        ) from error


def _base_url_from_card(card: Mapping[str, Any], agent_card_url: str) -> str:
    a2a_url = urlparse(str(card["url"]))
    if a2a_url.path.rstrip("/") == "/a2a":
        return _strip_trailing_slash(urlunparse((a2a_url.scheme, a2a_url.netloc, "/", "", "", "")))

    card_url = urlparse(agent_card_url)
    return _strip_trailing_slash(urlunparse((card_url.scheme, card_url.netloc, "/", "", "", "")))


def _strip_trailing_slash(value: str) -> str:
    return value.rstrip("/")
