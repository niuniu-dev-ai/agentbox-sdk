from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .client import AgentBoxClient, Transport
from .discovery import AgentBoxDiscovery, discover_agentbox


JsonMapping = Mapping[str, Any]


@dataclass(frozen=True)
class BootstrapAgentBoxAgentResult:
    discovery: AgentBoxDiscovery
    client: AgentBoxClient
    agent: Mapping[str, Any] | None


def bootstrap_agentbox_agent(
    *,
    base_url: str | None = None,
    agent_card_url: str | None = None,
    client: JsonMapping,
    registration: JsonMapping | None = None,
    transport: Transport | None = None,
    timeout: float | None = None,
) -> BootstrapAgentBoxAgentResult:
    discovery = discover_agentbox(
        base_url=base_url,
        agent_card_url=agent_card_url,
        transport=transport,
        timeout=timeout,
    )
    agent_client = discovery.create_client(**dict(client))
    agent = agent_client.register_agent(registration) if registration is not None else None
    return BootstrapAgentBoxAgentResult(discovery=discovery, client=agent_client, agent=None if agent is None else agent["data"])


def create_private_box_with_resources(
    client: AgentBoxClient,
    data: JsonMapping,
    **options: Any,
) -> dict[str, Any]:
    created = client.create_box(
        {
            "name": data["name"],
            **({"ttl_seconds": data["ttl_seconds"]} if data.get("ttl_seconds") is not None else {}),
            **({"metadata": data["metadata"]} if data.get("metadata") is not None else {}),
        },
        **options,
    )
    box_id = created["data"]["box"]["box_id"]
    items = []
    events = []
    artifacts = []

    for item in data.get("items") or []:
        items.append(client.put_item({"box_id": box_id, **dict(item)}, **options)["data"])

    for event in data.get("events") or []:
        events.append(client.append_event({"box_id": box_id, **dict(event)}, **options)["data"])

    for artifact in data.get("artifacts") or []:
        artifacts.append(client.attach_artifact({"box_id": box_id, **dict(artifact)}, **options)["data"])

    manifest = None
    if data.get("read_manifest", True):
        manifest = client.get_manifest({"box_id": box_id}, **options)["data"]

    return {
        "box": created["data"]["box"],
        "manifest_uri": created["data"]["manifest_uri"],
        "items": items,
        "events": events,
        "artifacts": artifacts,
        "manifest": manifest,
    }


def create_scoped_read_grant(
    client: AgentBoxClient,
    data: JsonMapping,
    **options: Any,
) -> dict[str, Any]:
    body = dict(data)
    body.setdefault("permissions", ["read"])
    return client.create_grant(body, **options)["data"]


def client_for_grant(
    client: AgentBoxClient,
    grant: JsonMapping,
    *,
    actor: str | None = None,
    identity_token: str | None = None,
    auth_scheme: str | None = None,
) -> AgentBoxClient:
    if identity_token:
        return client.with_auth(
            actor=actor,
            identity_token=identity_token,
            grant_token=str(grant["access_token"]),
            auth_scheme=auth_scheme,
        )

    return client.with_auth(
        actor=actor or str(grant["grant"]["subject"]),
        token=str(grant["access_token"]),
        auth_scheme="agentboxGrant",
    )
