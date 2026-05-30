export type JsonValue =
  | null
  | boolean
  | number
  | string
  | JsonValue[]
  | {
      [key: string]: JsonValue;
    };

export type JsonObject = {
  [key: string]: JsonValue;
};

export type BoxStatus = "open" | "closed" | "expired" | "purge_eligible";

export type AgentBoxPermission = "read" | "write" | "append" | "attach" | "share" | "admin";

export type AgentIdentityScheme = "pilot" | "oidc" | "spiffe" | "dev";

export interface AgentIdentity {
  scheme: AgentIdentityScheme;
  subject: string;
  issuer?: string;
  public_key_fingerprint?: string;
  display_name?: string;
  agent_card_url?: string;
}

export type KnownAgentStatus = "active" | "blocked";

export interface KnownAgentRecord {
  identity_key: string;
  identity: AgentIdentity;
  display_name: string | null;
  agent_card_url: string | null;
  capabilities: string[];
  status: KnownAgentStatus;
  metadata: JsonObject | null;
  first_seen_at: string;
  last_seen_at: string;
}

export interface BoxRecord {
  box_id: string;
  name: string;
  status: BoxStatus;
  created_by: string | null;
  owner_identity: AgentIdentity | null;
  created_at: string;
  updated_at: string;
  expires_at: string | null;
  metadata: JsonObject | null;
}

export interface BoxItemSummary {
  box_id: string;
  key: string;
  version: number;
  content_type: string;
  tags: string[];
  created_by: string | null;
  created_at: string;
  updated_by: string | null;
  updated_at: string;
}

export interface BoxItemRecord extends BoxItemSummary {
  value: JsonValue;
}

export interface BoxEventRecord {
  event_id: string;
  box_id: string;
  stream: string;
  seq: number;
  type: string;
  actor: string | null;
  payload: JsonObject | null;
  created_at: string;
}

export interface ArtifactSummary {
  artifact_id: string;
  box_id: string;
  name: string;
  content_type: string;
  size_bytes: number;
  sha256: string;
  created_by: string | null;
  created_at: string;
}

export interface ArtifactContent {
  artifact: ArtifactSummary;
  content_base64: string;
}

export interface PublicGrantRecord {
  grant_id: string;
  box_id: string;
  subject: string;
  subject_identity: AgentIdentity | null;
  permissions: AgentBoxPermission[];
  key_prefixes: string[] | null;
  event_streams: string[] | null;
  artifact_prefixes: string[] | null;
  created_by: string | null;
  created_at: string;
  expires_at: string;
  revoked_at: string | null;
}

export interface EventStreamSummary {
  name: string;
  last_seq: number;
}

export interface AuditRecord {
  audit_id: string;
  box_id: string | null;
  action: string;
  actor: string | null;
  actor_identity: AgentIdentity | null;
  target: string | null;
  payload: JsonObject | null;
  created_at: string;
}

export interface IdentityProviderSummary {
  name: string;
  type: "oidc";
  source: "legacy" | "named" | "stored";
  issuer: string | null;
  audience: string | null;
  jwks_url: string | null;
  subject_claim: string;
  display_name_claim: string | null;
  agent_card_url_claim: string | null;
  algorithms: string[] | null;
  clock_tolerance: string | number | null;
  max_token_age: string | number | null;
  advertised: boolean;
  open_id_connect_url: string | null;
  status?: "active" | "disabled";
}

export interface AdvertisedSecurityScheme {
  name: string;
  type: string;
  open_id_connect_url?: string | null;
  in?: string | null;
  scheme?: string | null;
}

export interface IdentityProviderOverview {
  providers: IdentityProviderSummary[];
  advertised_schemes: AdvertisedSecurityScheme[];
}

export interface IdentityProviderRecord {
  name: string;
  type: "oidc";
  issuer: string;
  audience: string;
  jwks_url: string;
  subject_claim: string | null;
  display_name_claim: string | null;
  agent_card_url_claim: string | null;
  algorithms: string[] | null;
  clock_tolerance: string | number | null;
  max_token_age: string | number | null;
  status: "active" | "disabled";
  created_by: string | null;
  created_at: string;
  updated_by: string | null;
  updated_at: string;
}

export interface AgentBoxManifest {
  box_id: string;
  name: string;
  status: BoxStatus;
  created_by: string | null;
  expires_at: string | null;
  items: BoxItemSummary[];
  streams: EventStreamSummary[];
  artifacts: ArtifactSummary[];
  active_claims: Array<{
    claim_id: string;
    key: string;
    claimed_by: string | null;
    expires_at: string;
  }>;
  recent_events: Array<{
    stream: string;
    seq: number;
    type: string;
    actor: string | null;
  }>;
}

export type FetchLike = (input: string | URL, init?: RequestInit) => Promise<Response>;

export interface AgentBoxClientOptions {
  baseUrl: string;
  actor?: string;
  token?: string;
  identityToken?: string;
  grantToken?: string;
  authScheme?: string;
  fetch?: FetchLike;
}

export interface AgentBoxDiscoveryOptions {
  baseUrl?: string;
  agentCardUrl?: string;
  fetch?: FetchLike;
}

export interface AgentBoxDiscoveredClientOptions extends Omit<AgentBoxClientOptions, "baseUrl" | "fetch"> {
  fetch?: FetchLike;
}

export interface AgentBoxAgentCard {
  protocolVersion?: string;
  name?: string;
  description?: string;
  url: string;
  securitySchemes?: JsonObject;
  security?: Array<Record<string, string[]>>;
  skills?: JsonObject[];
  usagePolicy?: JsonObject;
  [key: string]: JsonValue | undefined;
}

export interface AgentBoxResult<T> {
  ok: true;
  data: T;
  error: null;
  audit_id: string | null;
}

export interface AgentBoxErrorResponse {
  ok: false;
  data: null;
  error: {
    code: string;
    message: string;
    target?: string;
    request_id?: string;
  };
  audit_id: string | null;
}

export type CreateBoxResult = {
  box: BoxRecord;
  manifest_uri: string;
};

export type CreateGrantResult = {
  grant: PublicGrantRecord;
  access_token: string;
};

export interface RegisterAgentInput {
  display_name?: string;
  agent_card_url?: string;
  capabilities?: string[];
  metadata?: JsonObject;
}

export interface UpdateAgentStatusInput {
  identity_key: string;
  status: KnownAgentStatus;
}

export interface UpsertIdentityProviderInput {
  name: string;
  type: "oidc";
  issuer: string;
  audience: string;
  jwks_url: string;
  subject_claim?: string | null;
  display_name_claim?: string | null;
  agent_card_url_claim?: string | null;
  algorithms?: string[] | null;
  clock_tolerance?: string | number | null;
  max_token_age?: string | number | null;
  status?: "active" | "disabled";
}

export interface UpdateIdentityProviderInput {
  name: string;
  issuer?: string;
  audience?: string;
  jwks_url?: string;
  subject_claim?: string | null;
  display_name_claim?: string | null;
  agent_card_url_claim?: string | null;
  algorithms?: string[] | null;
  clock_tolerance?: string | number | null;
  max_token_age?: string | number | null;
  status?: "active" | "disabled";
}

export interface CreateBoxInput {
  name: string;
  ttl_seconds?: number;
  metadata?: JsonObject;
}

export interface PutItemInput {
  box_id: string;
  key: string;
  value: JsonValue;
  content_type?: string;
  tags?: string[];
  expected_version?: number;
}

export interface GetItemInput {
  box_id: string;
  key: string;
  version?: number | "latest";
}

export interface ListItemsInput {
  box_id: string;
  prefix?: string;
  tags?: string[];
  content_type?: string;
}

export interface AppendEventInput {
  box_id: string;
  stream: string;
  type: string;
  payload?: JsonObject;
}

export interface ListEventsInput {
  box_id: string;
  stream: string;
  after_seq?: number;
  limit?: number;
}

export interface AttachArtifactInput {
  box_id: string;
  name: string;
  content_type: string;
  content_base64: string;
}

export interface ListArtifactsInput {
  box_id: string;
}

export interface GetArtifactInput {
  box_id: string;
  artifact_id: string;
}

export interface CreateGrantInput {
  box_id: string;
  subject: string;
  subject_identity?: AgentIdentity;
  permissions: AgentBoxPermission[];
  ttl_seconds: number;
  key_prefixes?: string[];
  event_streams?: string[];
  artifact_prefixes?: string[];
}

export interface ListGrantsInput {
  box_id: string;
}

export interface RevokeGrantInput {
  box_id: string;
  grant_id: string;
}

export interface ListAuditInput {
  box_id: string;
}
