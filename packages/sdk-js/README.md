# AgentBox JavaScript SDK

TypeScript SDK for [AgentBox](https://agentbox.niuniu.dev/) private agent
state and scoped sharing.

Use the public production service at `https://agentbox.niuniu.dev/` for Agent
Card discovery and SDK integration. Discovery and package installation work
without private repository access.

## Install

```bash
npm install @niuniu-ai/agentbox
```

## Production Auth

Creating boxes in production requires an accepted AgentBox identity path.
Direct HTTPS clients can pass an OIDC identity token from a provider configured
by AgentBox, such as Google, as `identityToken` with the matching `authScheme`.
Native Pilot callers rely on a Pilot-aware runtime or the AgentBox Pilot
adapter to establish Pilot identity before requests reach AgentBox; SDK
application code should not set `authScheme: "pilot"` or handcraft Pilot
headers. When a recipient uses an AgentBox grant, keep the scoped grant token
separate from the identity token or Pilot identity.

## First Private Box With Google OIDC

Get a Google ID token for the Google OAuth client configured by AgentBox
production, then keep it outside source code:

```bash
export AGENTBOX_GOOGLE_ID_TOKEN='<google-id-token>'
```

The token must be a Google ID token, not an OAuth access token, and its `aud`
claim must match the Google OAuth client trusted by AgentBox.

```ts
import { discoverAgentBox } from "@niuniu-ai/agentbox";

const service = await discoverAgentBox({
  baseUrl: "https://agentbox.niuniu.dev"
});

const agentbox = service.createClient({
  identityToken: process.env.AGENTBOX_GOOGLE_ID_TOKEN!,
  authScheme: "google"
});

await agentbox.registerAgent({
  display_name: "My First Agent",
  capabilities: ["notes"]
});

const created = await agentbox.createBox({
  name: "First private box"
});

const boxId = created.data.box.box_id;

await agentbox.putItem({
  box_id: boxId,
  key: "notes/hello",
  value: "Hello from an identity-bound private box.",
  expected_version: 0
});

const manifest = await agentbox.getManifest({
  box_id: boxId
});

console.log(manifest.data.items.map((item) => item.key));
```

The box is private to the verified Google identity. To let another identity
read selected resources, create an AgentBox grant and pass that grant as
`grantToken` while the recipient still authenticates with its own Google ID
token.

## Discovery And Workflow

```ts
import {
  bootstrapAgentBoxAgent,
  clientForGrant,
  createPrivateBoxWithResources,
  createScopedReadGrant
} from "@niuniu-ai/agentbox";

const { client: research } = await bootstrapAgentBoxAgent({
  baseUrl: "https://agentbox.niuniu.dev",
  client: {
    identityToken: process.env.RESEARCH_OIDC_JWT!,
    authScheme: "google"
  },
  registration: {
    display_name: "Research Agent",
    capabilities: ["research"]
  }
});

const workspace = await createPrivateBoxWithResources(research, {
  name: "Research handoff",
  items: [
    {
      key: "research/summary",
      value: "Only this summary is shared.",
      expected_version: 0
    },
    {
      key: "state/internal",
      value: "Private notes stay hidden.",
      expected_version: 0
    }
  ]
});

const grant = await createScopedReadGrant(research, {
  box_id: workspace.box.box_id,
  subject: "writer-agent",
  key_prefixes: ["research/"],
  ttl_seconds: 3600
});

const writer = clientForGrant(research, grant, {
  identityToken: process.env.WRITER_OIDC_JWT!,
  authScheme: "google"
});

const manifest = await writer.getManifest({
  box_id: workspace.box.box_id
});
```

## Auth Modes

Direct AgentBox clients authenticate with OIDC identity tokens. Grant clients
can carry the AgentBox scoped grant separately with `grantToken`, or use
`clientForGrant(...)` to derive a least-privilege client from a grant response.
Pass `authScheme` for named providers such as `google`. Native Pilot identity
is handled by the runtime/adapter boundary rather than a separate SDK auth
mode.

## API Reference

Client options:

```ts
new AgentBoxClient({
  baseUrl: "https://agentbox.niuniu.dev",
  actor,
  token,
  identityToken,
  grantToken,
  authScheme,
  fetch
});
```

`token` and `identityToken` are mutually exclusive. Use `actor` with local or
admin token auth. Use `identityToken` plus a named `authScheme`, such as
`google`, for production OIDC auth. Keep AgentBox scoped grants separate as
`grantToken`.

Discovery and workflow helpers:

```text
discoverAgentBox({ baseUrl | agentCardUrl })
bootstrapAgentBoxAgent(input)
createPrivateBoxWithResources(client, input)
createScopedReadGrant(client, input)
clientForGrant(client, grant, input?)
```

Client methods:

```text
health()
registerAgent(input?)
getAgentProfile()
listAgents({ admin: true })
updateAgentStatus({ identity_key, status }, { admin: true })
createBox({ name, ttl_seconds?, metadata? })
listBoxes()
getManifest({ box_id })
putItem({ box_id, key, value, content_type?, tags?, expected_version? })
getItem({ box_id, key, version? })
listItems({ box_id, prefix?, tags?, content_type? })
appendEvent({ box_id, stream, type, payload? })
listEvents({ box_id, stream, after_seq?, limit? })
attachArtifact({ box_id, name, content_type, content_base64 })
listArtifacts({ box_id })
getArtifact({ box_id, artifact_id })
createGrant({ box_id, subject, permissions, ttl_seconds, key_prefixes?, event_streams?, artifact_prefixes? })
listGrants({ box_id })
revokeGrant({ box_id, grant_id })
listAudit({ box_id })
withAuth({ actor?, token?, identityToken?, grantToken?, authScheme? })
```

Methods return the AgentBox response envelope:

```json
{ "ok": true, "data": {}, "error": null, "audit_id": "aud_..." }
```

Non-2xx responses and AgentBox `{ "ok": false }` responses throw
`AgentBoxApiError` with `code`, `status`, `target`, `request_id`, and
`audit_id`.

## Pilot Network Usage

Native Pilot identity is provided by a Pilot-aware runtime or the AgentBox Pilot
adapter before requests reach AgentBox. SDK application code should keep using
normal box, item, artifact, grant, manifest, and audit methods. Do not set
`authScheme: "pilot"` or handcraft Pilot authentication headers in agent code;
that path is for the AgentBox adapter/runtime boundary. If a Pilot caller uses
an AgentBox grant, pass it as `grantToken`.

## License

MIT
