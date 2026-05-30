# AgentBox Python SDK

`niuniu-agentbox` wraps the AgentBox REST API for Python agents and applications.
The first SDK slice intentionally mirrors the JavaScript SDK auth model and REST
surface while staying dependency-free.

For the full method, input, response, auth, discovery, workflow, and error
reference, see [`docs/sdk-reference.md`](./sdk-reference.md).

## Installation

After publishing:

```bash
python3 -m pip install niuniu-agentbox
```

Publishing is gated on namespace, credentials, and version confirmation. Until
then, validate the release package locally with:

```bash
npm run release:check:sdk-python
```

## Installation From Source

```bash
python3 -m pip install ./packages/sdk-python
```

## Auth Modes

Local/admin compatibility auth uses an actor label and bearer token:

```python
from agentbox import AgentBoxClient

research = AgentBoxClient(
    base_url="http://127.0.0.1:3000",
    actor="research-agent",
    token="dev-token",
)
```

OIDC auth uses the identity JWT as the bearer token. If the same caller also
uses an AgentBox grant, pass that grant separately as `grant_token`:

```python
writer = AgentBoxClient(
    base_url="https://agent-box.example",
    identity_token="oidc.jwt.token",
    auth_scheme="google",
    grant_token="abx_grant_token",
)
```

`with_auth()` derives a new client with replacement credentials. Token auth and
OIDC auth are mutually exclusive; switching modes clears inherited credentials
from the previous mode.

```python
grant = research.create_grant({
    "box_id": box_id,
    "subject": "writer-agent",
    "permissions": ["read"],
    "key_prefixes": ["research/"],
    "ttl_seconds": 86400,
})

writer = research.with_auth(
    actor="writer-agent",
    token=grant["data"]["access_token"],
)
```

## Pilot Network Usage

The SDK does not expose a separate Pilot auth mode. Native Pilot identity is
established by the Pilot network and the AgentBox Pilot adapter before the
request reaches the REST API. Application code should keep using the normal SDK
box, item, artifact, grant, manifest, and audit methods.

When a Pilot-aware runtime provides an HTTP-compatible endpoint for AgentBox,
point the SDK at that runtime endpoint or pass a custom `transport`. Do not set
`auth_scheme="pilot"` or handcraft Pilot authentication headers in agent
application code. That path is reserved for the AgentBox adapter/runtime
boundary, not SDK clients.

Grant tokens are still application-level AgentBox credentials. A Pilot caller
that receives an AgentBox grant should pass it as `grant_token`; the Pilot
runtime remains responsible for the caller's network identity.

## Discovery

Agents can bootstrap from AgentBox's public A2A Agent Card instead of
hardcoding the REST base URL. Discovery reads `/.well-known/agent-card.json`,
derives the REST and A2A URLs, and returns an object that can create normal
authenticated clients.

```python
import os

from agentbox import discover_agentbox

discovery = discover_agentbox(base_url="https://agentbox.niuniu.dev")

print(discovery.a2a_url)
print(discovery.rest_api_base_url)
print(discovery.security_schemes.keys())

research = discovery.create_client(
    identity_token=os.environ["RESEARCH_OIDC_JWT"],
    auth_scheme="google",
)

research.register_agent({
    "display_name": "Research Agent",
    "agent_card_url": "https://agents.example/research/.well-known/agent-card.json",
    "capabilities": ["research", "summarize"],
})
```

## Workflow Helpers

The workflow helpers keep the security choices visible while reducing the glue
needed for the common private-storage plus scoped-sharing flow.

```python
import base64
import os

from agentbox import (
    bootstrap_agentbox_agent,
    client_for_grant,
    create_private_box_with_resources,
    create_scoped_read_grant,
)

session = bootstrap_agentbox_agent(
    base_url="https://agentbox.niuniu.dev",
    client={
        "identity_token": os.environ["RESEARCH_OIDC_JWT"],
        "auth_scheme": "google",
    },
    registration={
        "display_name": "Research Agent",
        "capabilities": ["research"],
    },
)

workspace = create_private_box_with_resources(session.client, {
    "name": "Research handoff",
    "items": [
        {
            "key": "research/summary",
            "value": "Only this summary is shared.",
            "expected_version": 0,
        },
        {
            "key": "state/internal",
            "value": "Private notes stay hidden.",
            "expected_version": 0,
        },
    ],
    "artifacts": [
        {
            "name": "public-brief.md",
            "content_type": "text/markdown",
            "content_base64": base64.b64encode(b"# Brief").decode("ascii"),
        }
    ],
})

grant = create_scoped_read_grant(session.client, {
    "box_id": workspace["box"]["box_id"],
    "subject": "writer-agent",
    "key_prefixes": ["research/"],
    "artifact_prefixes": ["public-"],
    "ttl_seconds": 3600,
})

writer = client_for_grant(
    session.client,
    grant,
    identity_token=os.environ["WRITER_OIDC_JWT"],
    auth_scheme="google",
)

manifest = writer.get_manifest({"box_id": workspace["box"]["box_id"]})
```

## Known-Agent Registry

The registry records internal metadata about an already-authenticated agent. It
does not issue or verify identity.

```python
registered = research.register_agent({
    "display_name": "Research Agent",
    "capabilities": ["research", "write"],
    "metadata": {"source": "python-sdk"},
})

profile = research.get_agent_profile()
agents = research.list_agents(admin=True)
blocked = research.update_agent_status({
    "identity_key": agents["data"][0]["identity_key"],
    "status": "blocked",
}, admin=True)
```

## Methods

The canonical cross-runtime API reference is
[`docs/sdk-reference.md`](./sdk-reference.md). The Python SDK exports:

```text
health()
discover_agentbox(base_url=... | agent_card_url=...)
bootstrap_agentbox_agent(...)
create_private_box_with_resources(client, data)
create_scoped_read_grant(client, data)
client_for_grant(client, grant, ...)
register_agent(data=None)
get_agent_profile()
list_agents(admin=True)
update_agent_status({"identity_key": ..., "status": "blocked"}, admin=True)
create_box(data)
list_boxes()
get_manifest({"box_id": ...})
put_item(data)
get_item(data)
list_items(data)
append_event(data)
list_events(data)
attach_artifact(data)
list_artifacts({"box_id": ...})
get_artifact(data)
create_grant(data)
list_grants({"box_id": ...})
revoke_grant(data)
list_audit({"box_id": ...})
with_auth(actor=None, token=None, identity_token=None, grant_token=None, auth_scheme=None)
```

All API methods return the AgentBox response envelope as a Python dictionary.
Non-2xx responses and AgentBox `{ "ok": false }` responses raise
`AgentBoxApiError` with `code`, `status`, `target`, `request_id`, and `audit_id`
attributes.
