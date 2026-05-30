# AgentBox Python SDK

Python SDK for [AgentBox](https://agentbox.niuniu.dev/) private agent state and
scoped sharing.

Use the public production service at `https://agentbox.niuniu.dev/` for Agent
Card discovery and SDK integration. Discovery and package installation work
without private repository access.

## Install

```bash
python3 -m pip install niuniu-agentbox
```

Import the SDK as `agentbox`:

```python
from agentbox import AgentBoxClient
```

## Production Auth

Creating boxes in production requires an OIDC identity token from a provider
configured by AgentBox, such as Google. Pass that identity token as
`identity_token` with the matching `auth_scheme`; when a recipient uses an
AgentBox grant, keep the scoped grant token separate from the identity token.

## First Private Box With Google OIDC

Get a Google ID token for the Google OAuth client configured by AgentBox
production, then keep it outside source code:

```bash
export AGENTBOX_GOOGLE_ID_TOKEN='<google-id-token>'
```

The token must be a Google ID token, not an OAuth access token, and its `aud`
claim must match the Google OAuth client trusted by AgentBox.

```python
import os

from agentbox import discover_agentbox

service = discover_agentbox(base_url="https://agentbox.niuniu.dev")

agentbox = service.create_client(
    identity_token=os.environ["AGENTBOX_GOOGLE_ID_TOKEN"],
    auth_scheme="google",
)

agentbox.register_agent({
    "display_name": "My First Agent",
    "capabilities": ["notes"],
})

created = agentbox.create_box({
    "name": "First private box",
})

box_id = created["data"]["box"]["box_id"]

agentbox.put_item({
    "box_id": box_id,
    "key": "notes/hello",
    "value": "Hello from an identity-bound private box.",
    "expected_version": 0,
})

manifest = agentbox.get_manifest({
    "box_id": box_id,
})

print([item["key"] for item in manifest["data"]["items"]])
```

The box is private to the verified Google identity. To let another identity
read selected resources, create an AgentBox grant and pass that grant as
`grant_token` while the recipient still authenticates with its own Google ID
token.

## Discovery And Workflow

```python
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
})

grant = create_scoped_read_grant(session.client, {
    "box_id": workspace["box"]["box_id"],
    "subject": "writer-agent",
    "key_prefixes": ["research/"],
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

## Auth Modes

AgentBox clients authenticate with OIDC identity tokens. Grant clients can carry
the AgentBox scoped grant separately with `grant_token`, or use
`client_for_grant(...)` to derive a least-privilege client from a grant response.
Pass `auth_scheme` for named providers such as `google`.

## API Reference

Client options:

```python
AgentBoxClient(
    base_url="https://agentbox.niuniu.dev",
    actor=actor,
    token=token,
    identity_token=identity_token,
    grant_token=grant_token,
    auth_scheme=auth_scheme,
    transport=transport,
    timeout=timeout,
)
```

`token` and `identity_token` are mutually exclusive. Use `actor` with local or
admin token auth. Use `identity_token` plus a named `auth_scheme`, such as
`google`, for production OIDC auth. Keep AgentBox scoped grants separate as
`grant_token`.

Discovery and workflow helpers:

```text
discover_agentbox(base_url=... | agent_card_url=...)
bootstrap_agentbox_agent(...)
create_private_box_with_resources(client, data)
create_scoped_read_grant(client, data)
client_for_grant(client, grant, ...)
```

Client methods:

```text
health()
register_agent(data=None)
get_agent_profile()
list_agents(admin=True)
update_agent_status({"identity_key": ..., "status": "blocked"}, admin=True)
create_box({"name": ..., "ttl_seconds": ..., "metadata": ...})
list_boxes()
get_manifest({"box_id": ...})
put_item({"box_id": ..., "key": ..., "value": ..., "expected_version": ...})
get_item({"box_id": ..., "key": ..., "version": ...})
list_items({"box_id": ..., "prefix": ..., "tags": ..., "content_type": ...})
append_event({"box_id": ..., "stream": ..., "type": ..., "payload": ...})
list_events({"box_id": ..., "stream": ..., "after_seq": ..., "limit": ...})
attach_artifact({"box_id": ..., "name": ..., "content_type": ..., "content_base64": ...})
list_artifacts({"box_id": ...})
get_artifact({"box_id": ..., "artifact_id": ...})
create_grant({"box_id": ..., "subject": ..., "permissions": ..., "ttl_seconds": ...})
list_grants({"box_id": ...})
revoke_grant({"box_id": ..., "grant_id": ...})
list_audit({"box_id": ...})
with_auth(actor=None, token=None, identity_token=None, grant_token=None, auth_scheme=None)
```

Methods return the AgentBox response envelope as a Python dictionary:

```json
{ "ok": true, "data": {}, "error": null, "audit_id": "aud_..." }
```

Non-2xx responses and AgentBox `{ "ok": false }` responses raise
`AgentBoxApiError` with `code`, `status`, `target`, `request_id`, and
`audit_id` attributes.

## Pilot Network Usage

Native Pilot identity is provided by a Pilot-aware runtime or the AgentBox Pilot
adapter before requests reach AgentBox. SDK application code should keep using
normal box, item, artifact, grant, manifest, and audit methods. Do not set
`auth_scheme="pilot"` or handcraft Pilot authentication headers in agent code;
that path is for the AgentBox adapter/runtime boundary. If a Pilot caller uses
an AgentBox grant, pass it as `grant_token`.

## License

MIT
