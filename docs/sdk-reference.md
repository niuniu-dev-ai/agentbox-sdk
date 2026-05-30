# AgentBox SDK API Reference

This reference covers the public JavaScript and Python SDK surfaces for
AgentBox. The SDKs wrap the REST API response envelope:

```json
{
  "ok": true,
  "data": {},
  "error": null,
  "audit_id": "aud_..."
}
```

JavaScript methods return `Promise<AgentBoxResult<T>>`. Python methods return
the same envelope as a dictionary.

## Packages

| Runtime | Package | Import |
| --- | --- | --- |
| JavaScript/TypeScript | `@niuniu-ai/agentbox` | `import { AgentBoxClient } from "@niuniu-ai/agentbox";` |
| Python | `niuniu-agentbox` | `from agentbox import AgentBoxClient` |

## Authentication

AgentBox supports two SDK-facing auth forms.

| Mode | JavaScript options | Python options | Headers |
| --- | --- | --- | --- |
| Local/admin compatibility | `actor`, `token` | `actor`, `token` | `Authorization: Bearer <token>`, `x-agentbox-actor: <actor>` |
| OIDC identity | `identityToken`, optional `authScheme`, optional `grantToken` | `identity_token`, optional `auth_scheme`, optional `grant_token` | `Authorization: Bearer <identity-token>`, optional `x-agentbox-auth-scheme`, optional `x-agentbox-grant-token` |

`token` and `identityToken` / `identity_token` are mutually exclusive. Grant
tokens are separate AgentBox credentials and should stay separate from the
caller's identity token.

Native Pilot identity is not a separate SDK auth mode. Pilot-aware runtimes or
the AgentBox Pilot adapter establish Pilot identity before the request reaches
AgentBox. SDK code should continue to use normal box, item, artifact, grant,
manifest, and audit methods. Do not set `authScheme: "pilot"` /
`auth_scheme="pilot"` or handcraft Pilot bridge headers in application code.

## Client Constructors

### JavaScript

```ts
const client = new AgentBoxClient({
  baseUrl: "https://agentbox.niuniu.dev",
  identityToken: process.env.AGENTBOX_GOOGLE_ID_TOKEN!,
  authScheme: "google",
  grantToken: process.env.AGENTBOX_GRANT_TOKEN,
  fetch: customFetch
});
```

Options:

- `baseUrl`: AgentBox service base URL.
- `actor`: required with local/admin token auth.
- `token`: local/admin bearer token or legacy grant token.
- `identityToken`: OIDC identity token.
- `grantToken`: AgentBox scoped grant token used with an identity token.
- `authScheme`: named provider such as `google`.
- `fetch`: optional custom `fetch` implementation.

### Python

```python
client = AgentBoxClient(
    base_url="https://agentbox.niuniu.dev",
    identity_token=os.environ["AGENTBOX_GOOGLE_ID_TOKEN"],
    auth_scheme="google",
    grant_token=os.environ.get("AGENTBOX_GRANT_TOKEN"),
    timeout=30,
)
```

Options:

- `base_url`: AgentBox service base URL.
- `actor`: required with local/admin token auth.
- `token`: local/admin bearer token or legacy grant token.
- `identity_token`: OIDC identity token.
- `grant_token`: AgentBox scoped grant token used with an identity token.
- `auth_scheme`: named provider such as `google`.
- `transport`: optional custom transport callable.
- `timeout`: optional request timeout passed to the transport.

## Discovery

Discovery reads the public A2A Agent Card and derives the REST and A2A URLs.

| JavaScript | Python | Description |
| --- | --- | --- |
| `discoverAgentBox({ baseUrl })` | `discover_agentbox(base_url=...)` | Read `/.well-known/agent-card.json` from a service base URL. |
| `discoverAgentBox({ agentCardUrl })` | `discover_agentbox(agent_card_url=...)` | Read an explicit Agent Card URL. |

Discovery results include:

- `agentCardUrl` / `agent_card_url`
- `baseUrl` / `base_url`
- `a2aUrl` / `a2a_url`
- `restApiBaseUrl` / `rest_api_base_url`
- `name`
- `description`
- `securitySchemes` / `security_schemes`
- `agentCard` / `agent_card`
- `createClient(...)` / `create_client(...)`

## Client Methods

All authenticated methods accept per-request auth overrides. JavaScript passes
them as the optional second argument. Python passes them as keyword arguments.
Use this for admin-only reads, short-lived grants, or one-off credential
rotation.

| JavaScript | Python | Input | Returns |
| --- | --- | --- | --- |
| `health()` | `health()` | none | `{ status }` |
| `registerAgent(input?)` | `register_agent(data=None)` | `RegisterAgentInput` | `KnownAgentRecord` |
| `getAgentProfile()` | `get_agent_profile()` | none | `KnownAgentRecord | null` |
| `listAgents()` | `list_agents()` | optional `{ admin: true }` override | `KnownAgentRecord[]` |
| `updateAgentStatus(input)` | `update_agent_status(data)` | `identity_key`, `status` | `KnownAgentRecord` |
| `createBox(input)` | `create_box(data)` | `CreateBoxInput` | `{ box, manifest_uri }` |
| `listBoxes()` | `list_boxes()` | none | `BoxRecord[]` |
| `getManifest(input)` | `get_manifest(data)` | `box_id` | `AgentBoxManifest` |
| `putItem(input)` | `put_item(data)` | `PutItemInput` | `BoxItemRecord` |
| `getItem(input)` | `get_item(data)` | `box_id`, `key`, optional `version` | `BoxItemRecord` |
| `listItems(input)` | `list_items(data)` | `box_id`, optional `prefix`, `tags`, `content_type` | `BoxItemSummary[]` |
| `appendEvent(input)` | `append_event(data)` | `AppendEventInput` | `BoxEventRecord` |
| `listEvents(input)` | `list_events(data)` | `box_id`, `stream`, optional `after_seq`, `limit` | `BoxEventRecord[]` |
| `attachArtifact(input)` | `attach_artifact(data)` | `AttachArtifactInput` | `ArtifactSummary` |
| `listArtifacts(input)` | `list_artifacts(data)` | `box_id` | `ArtifactSummary[]` |
| `getArtifact(input)` | `get_artifact(data)` | `box_id`, `artifact_id` | `{ artifact, content_base64 }` |
| `createGrant(input)` | `create_grant(data)` | `CreateGrantInput` | `{ grant, access_token }` |
| `listGrants(input)` | `list_grants(data)` | `box_id` | `PublicGrantRecord[]` |
| `revokeGrant(input)` | `revoke_grant(data)` | `box_id`, `grant_id` | `PublicGrantRecord` |
| `listAudit(input)` | `list_audit(data)` | `box_id` | `AuditRecord[]` |
| `withAuth(options)` | `with_auth(...)` | replacement auth options | new client |

## Common Inputs

### RegisterAgentInput

- `display_name`
- `agent_card_url`
- `capabilities`
- `metadata`

Registration records metadata about the already-authenticated caller. It does
not issue or verify identity.

### CreateBoxInput

- `name`
- `ttl_seconds`
- `metadata`

Boxes are private to the authenticated identity unless shared with an AgentBox
grant.

### PutItemInput

- `box_id`
- `key`
- `value`
- `content_type`
- `tags`
- `expected_version`

Use `expected_version` for optimistic concurrency. Use `0` when creating a new
item that must not overwrite an existing key.

### AppendEventInput

- `box_id`
- `stream`
- `type`
- `payload`

Events are append-only records scoped to a box stream.

### AttachArtifactInput

- `box_id`
- `name`
- `content_type`
- `content_base64`

Artifact reads return metadata plus base64 content. SDKs do not expose internal
object-storage URLs.

### CreateGrantInput

- `box_id`
- `subject`
- `subject_identity`
- `permissions`
- `ttl_seconds`
- `key_prefixes`
- `event_streams`
- `artifact_prefixes`

Permissions are `read`, `write`, `append`, `attach`, `share`, and `admin`.
Prefix and stream scopes make grants least-privilege.

## Workflow Helpers

| JavaScript | Python | Purpose |
| --- | --- | --- |
| `bootstrapAgentBoxAgent(input)` | `bootstrap_agentbox_agent(...)` | Discover AgentBox, create a client, and optionally register the caller. |
| `createPrivateBoxWithResources(client, input)` | `create_private_box_with_resources(client, data)` | Create a private box, seed items/events/artifacts, and read the manifest by default. |
| `createScopedReadGrant(client, input)` | `create_scoped_read_grant(client, data)` | Create a read grant, defaulting `permissions` to `["read"]`. |
| `clientForGrant(client, grant, options?)` | `client_for_grant(client, grant, ...)` | Derive a client that uses a grant token. |

`clientForGrant` / `client_for_grant` supports two forms:

- With an identity token: keeps the identity token as the bearer credential and
  sends the AgentBox grant as `grantToken` / `grant_token`.
- Without an identity token: uses the grant access token as the bearer token
  with the grant subject as the actor.

## Errors

JavaScript throws `AgentBoxApiError`. Python raises `AgentBoxApiError`.

The error includes:

- `code`
- `message`
- `status`
- `target`
- `request_id`
- `audit_id`

Non-2xx HTTP responses and AgentBox `{ "ok": false }` responses are surfaced
through this error type.

## REST API

For wire-level routes, environment variables, and deployment smoke tests, see
[`docs/rest-api.md`](./rest-api.md). Hosted AgentBox serves the machine-readable
REST contract at `https://agentbox.niuniu.dev/openapi.json` and the
human-readable API docs at `https://agentbox.niuniu.dev/api-docs`.
