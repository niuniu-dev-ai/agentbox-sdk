# AgentBox JavaScript SDK

`@niuniu-ai/agentbox` is a typed wrapper around the AgentBox REST API for agent
developers and application developers.

For the full method, input, response, auth, discovery, workflow, and error
reference, see [`docs/sdk-reference.md`](./sdk-reference.md).

## Installation

```bash
npm install @niuniu-ai/agentbox
```

Publishing is gated on namespace, credentials, and version confirmation. Until
then, validate the release package locally with:

```bash
npm run release:check:sdk-js
```

The SDK makes the security model explicit. Every client has:

- `baseUrl`
- either `actor` + `token` for local/admin or grant-token compatibility
- or `identityToken` for OIDC identity proof
- optional `grantToken` when an OIDC-authenticated caller uses an AgentBox grant
- optional `authScheme` when selecting a named provider such as `google`

The local/admin compatibility form sends:

```text
Authorization: Bearer <token>
x-agentbox-actor: <actor>
```

The OIDC form sends:

```text
Authorization: Bearer <identityToken>
x-agentbox-auth-scheme: <authScheme>  # for named providers such as google
x-agentbox-grant-token: <grantToken>  # only when using a grant
```

## Pilot Network Usage

The SDK does not expose a separate Pilot auth mode. Native Pilot identity is
established by the Pilot network and the AgentBox Pilot adapter before the
request reaches the REST API. Application code should keep using the normal SDK
box, item, artifact, grant, manifest, and audit methods.

When a Pilot-aware runtime provides an HTTP-compatible endpoint for AgentBox,
point the SDK at that runtime endpoint or provide a custom `fetch` transport.
Do not set `authScheme: "pilot"` or handcraft Pilot authentication headers in
agent application code. That path is reserved for the AgentBox adapter/runtime
boundary, not SDK clients.

Grant tokens are still application-level AgentBox credentials. A Pilot caller
that receives an AgentBox grant should pass it as `grantToken`; the Pilot
runtime remains responsible for the caller's network identity.

## Discovery

Agents can bootstrap from AgentBox's public A2A Agent Card instead of
hardcoding the REST base URL. Discovery does not authenticate the caller; it
reads `/.well-known/agent-card.json`, derives the REST and A2A URLs, and then
creates normal authenticated clients.

```ts
import { discoverAgentBox } from "@niuniu-ai/agentbox";

const discovery = await discoverAgentBox({
  baseUrl: "https://agentbox.niuniu.dev"
});

console.log(discovery.a2aUrl);
console.log(discovery.restApiBaseUrl);
console.log(Object.keys(discovery.securitySchemes));

const research = discovery.createClient({
  identityToken: process.env.RESEARCH_OIDC_JWT!,
  authScheme: "google"
});

await research.registerAgent({
  display_name: "Research Agent",
  agent_card_url: "https://agents.example/research/.well-known/agent-card.json",
  capabilities: ["research", "summarize"]
});
```

## Workflow Helpers

The workflow helpers keep the security choices visible while reducing the glue
needed for the common private-storage plus scoped-sharing flow.

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
  ],
  artifacts: [
    {
      name: "public-brief.md",
      content_type: "text/markdown",
      content_base64: Buffer.from("# Brief").toString("base64")
    }
  ]
});

const grant = await createScopedReadGrant(research, {
  box_id: workspace.box.box_id,
  subject: "writer-agent",
  key_prefixes: ["research/"],
  artifact_prefixes: ["public-"],
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

## Owner/Admin Usage

```ts
import { AgentBoxClient } from "@niuniu-ai/agentbox";

const research = new AgentBoxClient({
  baseUrl: "http://127.0.0.1:3000",
  actor: "research-agent",
  token: process.env.AGENTBOX_ADMIN_TOKEN!
});

const created = await research.createBox({
  name: "Research agent private store"
});

await research.putItem({
  box_id: created.data.box.box_id,
  key: "research/summary",
  value: "Three competitors focus on memory, not scoped resource sharing.",
  content_type: "text/plain",
  tags: ["research"],
  expected_version: 0
});

await research.attachArtifact({
  box_id: created.data.box.box_id,
  name: "final-report.md",
  content_type: "text/markdown",
  content_base64: Buffer.from("# Final report").toString("base64")
});
```

## Grant Usage

```ts
const grant = await research.createGrant({
  box_id,
  subject: "writer-agent",
  permissions: ["read", "append"],
  key_prefixes: ["research/"],
  event_streams: ["activity"],
  artifact_prefixes: ["public-"],
  ttl_seconds: 86400
});

const writer = research.withAuth({
  actor: "writer-agent",
  token: grant.data.access_token
});

const summary = await writer.getItem({
  box_id,
  key: "research/summary"
});
```

With OIDC, keep the identity token and AgentBox grant token separate:

```ts
const writer = new AgentBoxClient({
  baseUrl: "https://agent-box.example",
  identityToken: process.env.WRITER_OIDC_JWT!,
  grantToken: grant.data.access_token
});
```

Grant resource scopes are least-privilege. If a grant has only
`artifact_prefixes`, it can read matching artifacts but not items or event
streams.

Owners/admins and grant holders with `share` permission can revoke grants and
read box audit records.

## Methods

The canonical cross-runtime API reference is
[`docs/sdk-reference.md`](./sdk-reference.md). The JavaScript SDK exports:

```text
health()
discoverAgentBox({ baseUrl | agentCardUrl })
bootstrapAgentBoxAgent(input)
createPrivateBoxWithResources(client, input)
createScopedReadGrant(client, input)
clientForGrant(client, grant, input?)
registerAgent(input?)
getAgentProfile()
listAgents({ admin: true })
updateAgentStatus({ identity_key, status }, { admin: true })
createBox(input)
listBoxes()
getManifest({ box_id })
putItem(input)
getItem(input)
listItems(input)
appendEvent(input)
listEvents(input)
attachArtifact(input)
listArtifacts({ box_id })
getArtifact({ box_id, artifact_id })
createGrant(input)
listGrants({ box_id })
revokeGrant({ box_id, grant_id })
listAudit({ box_id })
withAuth({ actor?, token?, identityToken?, grantToken?, authScheme? })
```

Artifact reads return metadata plus `content_base64`. The SDK does not expose
internal storage URIs.

## Errors

Non-2xx responses and AgentBox `{ ok: false }` responses throw
`AgentBoxApiError`.

```ts
import { AgentBoxApiError } from "@niuniu-ai/agentbox";

try {
  await writer.getItem({ box_id, key: "state/internal" });
} catch (error) {
  if (error instanceof AgentBoxApiError) {
    console.log(error.code, error.status, error.target);
  }
}
```
