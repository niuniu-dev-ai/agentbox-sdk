import { AgentBoxClient } from "./client.js";
import { discoverAgentBox, type AgentBoxDiscovery } from "./discovery.js";
import type { AgentBoxClientRequestOptions } from "./client.js";
import type {
  AgentBoxDiscoveryOptions,
  AgentBoxDiscoveredClientOptions,
  AgentBoxManifest,
  AgentBoxPermission,
  AgentIdentity,
  AppendEventInput,
  ArtifactSummary,
  AttachArtifactInput,
  BoxEventRecord,
  BoxItemRecord,
  BoxRecord,
  CreateGrantResult,
  JsonObject,
  KnownAgentRecord,
  PutItemInput,
  RegisterAgentInput
} from "./types.js";

export interface BootstrapAgentBoxAgentInput extends AgentBoxDiscoveryOptions {
  client: AgentBoxDiscoveredClientOptions;
  registration?: RegisterAgentInput;
}

export interface BootstrapAgentBoxAgentResult {
  discovery: AgentBoxDiscovery;
  client: AgentBoxClient;
  agent: KnownAgentRecord | null;
}

export interface InitialBoxItemInput extends Omit<PutItemInput, "box_id"> {}

export interface InitialBoxEventInput extends Omit<AppendEventInput, "box_id"> {}

export interface InitialBoxArtifactInput extends Omit<AttachArtifactInput, "box_id"> {}

export interface CreatePrivateBoxWorkflowInput {
  name: string;
  ttl_seconds?: number;
  metadata?: JsonObject;
  items?: InitialBoxItemInput[];
  events?: InitialBoxEventInput[];
  artifacts?: InitialBoxArtifactInput[];
  readManifest?: boolean;
}

export interface CreatePrivateBoxWorkflowResult {
  box: BoxRecord;
  manifest_uri: string;
  items: BoxItemRecord[];
  events: BoxEventRecord[];
  artifacts: ArtifactSummary[];
  manifest: AgentBoxManifest | null;
}

export interface CreateScopedReadGrantInput {
  box_id: string;
  subject: string;
  subject_identity?: AgentIdentity;
  ttl_seconds: number;
  key_prefixes?: string[];
  event_streams?: string[];
  artifact_prefixes?: string[];
  permissions?: AgentBoxPermission[];
}

export interface GrantClientOptions {
  actor?: string;
  identityToken?: string;
  authScheme?: string;
}

export async function bootstrapAgentBoxAgent(input: BootstrapAgentBoxAgentInput): Promise<BootstrapAgentBoxAgentResult> {
  const discovery = await discoverAgentBox(input);
  const client = discovery.createClient(input.client);
  const agent = input.registration ? (await client.registerAgent(input.registration)).data : null;
  return {
    discovery,
    client,
    agent
  };
}

export async function createPrivateBoxWithResources(
  client: AgentBoxClient,
  input: CreatePrivateBoxWorkflowInput,
  options?: AgentBoxClientRequestOptions
): Promise<CreatePrivateBoxWorkflowResult> {
  const created = await client.createBox(
    {
      name: input.name,
      ttl_seconds: input.ttl_seconds,
      metadata: input.metadata
    },
    options
  );
  const boxId = created.data.box.box_id;
  const items: BoxItemRecord[] = [];
  const events: BoxEventRecord[] = [];
  const artifacts: ArtifactSummary[] = [];

  for (const item of input.items ?? []) {
    items.push(
      (
        await client.putItem(
          {
            box_id: boxId,
            ...item
          },
          options
        )
      ).data
    );
  }

  for (const event of input.events ?? []) {
    events.push(
      (
        await client.appendEvent(
          {
            box_id: boxId,
            ...event
          },
          options
        )
      ).data
    );
  }

  for (const artifact of input.artifacts ?? []) {
    artifacts.push(
      (
        await client.attachArtifact(
          {
            box_id: boxId,
            ...artifact
          },
          options
        )
      ).data
    );
  }

  const manifest = input.readManifest === false ? null : (await client.getManifest({ box_id: boxId }, options)).data;

  return {
    box: created.data.box,
    manifest_uri: created.data.manifest_uri,
    items,
    events,
    artifacts,
    manifest
  };
}

export async function createScopedReadGrant(
  client: AgentBoxClient,
  input: CreateScopedReadGrantInput,
  options?: AgentBoxClientRequestOptions
): Promise<CreateGrantResult> {
  return (
    await client.createGrant(
      {
        ...input,
        permissions: input.permissions ?? ["read"]
      },
      options
    )
  ).data;
}

export function clientForGrant(
  client: AgentBoxClient,
  grant: CreateGrantResult,
  options: GrantClientOptions = {}
): AgentBoxClient {
  if (options.identityToken) {
    return client.withAuth({
      identityToken: options.identityToken,
      grantToken: grant.access_token,
      authScheme: options.authScheme,
      actor: options.actor
    });
  }

  return client.withAuth({
    actor: options.actor ?? grant.grant.subject,
    token: grant.access_token,
    authScheme: "agentboxGrant"
  });
}
