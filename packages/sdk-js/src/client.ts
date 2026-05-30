import { AgentBoxApiError } from "./errors.js";
import type {
  AgentBoxErrorResponse,
  AgentBoxManifest,
  AgentBoxClientOptions,
  AgentBoxResult,
  AppendEventInput,
  ArtifactContent,
  ArtifactSummary,
  AttachArtifactInput,
  AuditRecord,
  BoxEventRecord,
  BoxItemRecord,
  BoxItemSummary,
  BoxRecord,
  CreateBoxInput,
  CreateBoxResult,
  CreateGrantInput,
  CreateGrantResult,
  FetchLike,
  GetArtifactInput,
  GetItemInput,
  IdentityProviderRecord,
  IdentityProviderOverview,
  KnownAgentRecord,
  ListArtifactsInput,
  ListEventsInput,
  ListGrantsInput,
  ListItemsInput,
  PublicGrantRecord,
  PutItemInput,
  RegisterAgentInput,
  RevokeGrantInput,
  UpdateIdentityProviderInput,
  UpdateAgentStatusInput,
  UpsertIdentityProviderInput,
  ListAuditInput
} from "./types.js";

export interface AgentBoxClientRequestOptions {
  token?: string;
  identityToken?: string;
  grantToken?: string;
  authScheme?: string;
  actor?: string;
  admin?: boolean;
}

export class AgentBoxClient {
  private readonly baseUrl: URL;
  private readonly actor?: string;
  private readonly token?: string;
  private readonly identityToken?: string;
  private readonly grantToken?: string;
  private readonly authScheme?: string;
  private readonly fetchImpl: FetchLike;

  constructor(options: AgentBoxClientOptions) {
    const actor = optionalNonEmpty(options.actor);
    const token = optionalNonEmpty(options.token);
    const identityToken = optionalNonEmpty(options.identityToken);
    const grantToken = optionalNonEmpty(options.grantToken);
    const authScheme = optionalNonEmpty(options.authScheme);

    if (token && identityToken) {
      throw new TypeError("AgentBoxClient token and identityToken auth modes are mutually exclusive.");
    }

    if (!token && !identityToken) {
      throw new TypeError("AgentBoxClient requires a token or identityToken.");
    }

    if (!identityToken && !actor) {
      throw new TypeError("AgentBoxClient requires a non-empty actor when using token auth.");
    }

    this.baseUrl = new URL(ensureTrailingSlash(options.baseUrl));
    this.actor = actor;
    this.token = token;
    this.identityToken = identityToken;
    this.grantToken = grantToken;
    this.authScheme = authScheme;
    this.fetchImpl = safeFetch(options.fetch);
  }

  health(): Promise<AgentBoxResult<{ status: string }>> {
    return this.request({
      method: "GET",
      path: "/health",
      auth: false
    });
  }

  createBox(input: CreateBoxInput, options?: AgentBoxClientRequestOptions): Promise<AgentBoxResult<CreateBoxResult>> {
    return this.request({
      method: "POST",
      path: "/v1/boxes",
      body: input,
      options
    });
  }

  registerAgent(
    input: RegisterAgentInput = {},
    options?: AgentBoxClientRequestOptions
  ): Promise<AgentBoxResult<KnownAgentRecord>> {
    return this.request({
      method: "POST",
      path: "/v1/agents/register",
      body: input,
      options
    });
  }

  getAgentProfile(options?: AgentBoxClientRequestOptions): Promise<AgentBoxResult<KnownAgentRecord | null>> {
    return this.request({
      method: "GET",
      path: "/v1/agents/me",
      options
    });
  }

  listAgents(options?: AgentBoxClientRequestOptions): Promise<AgentBoxResult<KnownAgentRecord[]>> {
    return this.request({
      method: "GET",
      path: "/v1/agents",
      options
    });
  }

  getIdentityProviderOverview(
    options?: AgentBoxClientRequestOptions
  ): Promise<AgentBoxResult<IdentityProviderOverview>> {
    return this.request({
      method: "GET",
      path: "/v1/admin/identity-providers",
      options
    });
  }

  upsertIdentityProvider(
    input: UpsertIdentityProviderInput,
    options?: AgentBoxClientRequestOptions
  ): Promise<AgentBoxResult<IdentityProviderRecord>> {
    return this.request({
      method: "POST",
      path: "/v1/admin/identity-providers",
      body: input,
      options
    });
  }

  updateIdentityProvider(
    input: UpdateIdentityProviderInput,
    options?: AgentBoxClientRequestOptions
  ): Promise<AgentBoxResult<IdentityProviderRecord>> {
    const { name, ...body } = input;
    return this.request({
      method: "PATCH",
      path: `/v1/admin/identity-providers/${encodePathSegment(name)}`,
      body,
      options
    });
  }

  updateAgentStatus(
    input: UpdateAgentStatusInput,
    options?: AgentBoxClientRequestOptions
  ): Promise<AgentBoxResult<KnownAgentRecord>> {
    const { identity_key, ...body } = input;
    return this.request({
      method: "PATCH",
      path: `/v1/agents/${encodePathSegment(identity_key)}/status`,
      body,
      options
    });
  }

  listBoxes(options?: AgentBoxClientRequestOptions): Promise<AgentBoxResult<BoxRecord[]>> {
    return this.request({
      method: "GET",
      path: "/v1/boxes",
      options
    });
  }

  getManifest(
    input: { box_id: string },
    options?: AgentBoxClientRequestOptions
  ): Promise<AgentBoxResult<AgentBoxManifest>> {
    return this.request({
      method: "GET",
      path: `/v1/boxes/${encodePathSegment(input.box_id)}/manifest`,
      options
    });
  }

  putItem(input: PutItemInput, options?: AgentBoxClientRequestOptions): Promise<AgentBoxResult<BoxItemRecord>> {
    const { box_id, key, ...body } = input;
    return this.request({
      method: "PUT",
      path: `/v1/boxes/${encodePathSegment(box_id)}/items/${encodeKeyPath(key)}`,
      body,
      options
    });
  }

  getItem(input: GetItemInput, options?: AgentBoxClientRequestOptions): Promise<AgentBoxResult<BoxItemRecord>> {
    const query = new URLSearchParams();
    if (input.version !== undefined) {
      query.set("version", String(input.version));
    }

    return this.request({
      method: "GET",
      path: `/v1/boxes/${encodePathSegment(input.box_id)}/items/${encodeKeyPath(input.key)}`,
      query,
      options
    });
  }

  listItems(input: ListItemsInput, options?: AgentBoxClientRequestOptions): Promise<AgentBoxResult<BoxItemSummary[]>> {
    const query = new URLSearchParams();
    if (input.prefix) {
      query.set("prefix", input.prefix);
    }
    if (input.content_type) {
      query.set("content_type", input.content_type);
    }
    if (input.tags?.length) {
      query.set("tags", input.tags.join(","));
    }

    return this.request({
      method: "GET",
      path: `/v1/boxes/${encodePathSegment(input.box_id)}/items`,
      query,
      options
    });
  }

  appendEvent(
    input: AppendEventInput,
    options?: AgentBoxClientRequestOptions
  ): Promise<AgentBoxResult<BoxEventRecord>> {
    const { box_id, stream, ...body } = input;
    return this.request({
      method: "POST",
      path: `/v1/boxes/${encodePathSegment(box_id)}/events/${encodePathSegment(stream)}`,
      body,
      options
    });
  }

  listEvents(
    input: ListEventsInput,
    options?: AgentBoxClientRequestOptions
  ): Promise<AgentBoxResult<BoxEventRecord[]>> {
    const query = new URLSearchParams();
    if (input.after_seq !== undefined) {
      query.set("after_seq", String(input.after_seq));
    }
    if (input.limit !== undefined) {
      query.set("limit", String(input.limit));
    }

    return this.request({
      method: "GET",
      path: `/v1/boxes/${encodePathSegment(input.box_id)}/events/${encodePathSegment(input.stream)}`,
      query,
      options
    });
  }

  attachArtifact(
    input: AttachArtifactInput,
    options?: AgentBoxClientRequestOptions
  ): Promise<AgentBoxResult<ArtifactSummary>> {
    const { box_id, ...body } = input;
    return this.request({
      method: "POST",
      path: `/v1/boxes/${encodePathSegment(box_id)}/artifacts`,
      body,
      options
    });
  }

  listArtifacts(
    input: ListArtifactsInput,
    options?: AgentBoxClientRequestOptions
  ): Promise<AgentBoxResult<ArtifactSummary[]>> {
    return this.request({
      method: "GET",
      path: `/v1/boxes/${encodePathSegment(input.box_id)}/artifacts`,
      options
    });
  }

  getArtifact(
    input: GetArtifactInput,
    options?: AgentBoxClientRequestOptions
  ): Promise<AgentBoxResult<ArtifactContent>> {
    return this.request({
      method: "GET",
      path: `/v1/boxes/${encodePathSegment(input.box_id)}/artifacts/${encodePathSegment(input.artifact_id)}`,
      options
    });
  }

  createGrant(
    input: CreateGrantInput,
    options?: AgentBoxClientRequestOptions
  ): Promise<AgentBoxResult<CreateGrantResult>> {
    const { box_id, ...body } = input;
    return this.request({
      method: "POST",
      path: `/v1/boxes/${encodePathSegment(box_id)}/grants`,
      body,
      options
    });
  }

  listGrants(
    input: ListGrantsInput,
    options?: AgentBoxClientRequestOptions
  ): Promise<AgentBoxResult<PublicGrantRecord[]>> {
    return this.request({
      method: "GET",
      path: `/v1/boxes/${encodePathSegment(input.box_id)}/grants`,
      options
    });
  }

  revokeGrant(
    input: RevokeGrantInput,
    options?: AgentBoxClientRequestOptions
  ): Promise<AgentBoxResult<PublicGrantRecord>> {
    return this.request({
      method: "POST",
      path: `/v1/boxes/${encodePathSegment(input.box_id)}/grants/${encodePathSegment(input.grant_id)}/revoke`,
      body: {},
      options
    });
  }

  listAudit(input: ListAuditInput, options?: AgentBoxClientRequestOptions): Promise<AgentBoxResult<AuditRecord[]>> {
    return this.request({
      method: "GET",
      path: `/v1/boxes/${encodePathSegment(input.box_id)}/audit`,
      options
    });
  }

  withAuth(options: AgentBoxClientRequestOptions): AgentBoxClient {
    const token = optionalNonEmpty(options.token);
    const identityToken = optionalNonEmpty(options.identityToken);
    const grantToken = optionalNonEmpty(options.grantToken);

    if (token && identityToken) {
      throw new TypeError("AgentBoxClient token and identityToken auth modes are mutually exclusive.");
    }

    if (identityToken) {
      return new AgentBoxClient({
        baseUrl: this.baseUrl.toString(),
        actor: this.identityToken ? options.actor ?? this.actor : options.actor,
        identityToken,
        grantToken,
        authScheme: optionalNonEmpty(options.authScheme) ?? (this.identityToken ? this.authScheme : undefined),
        fetch: this.fetchImpl
      });
    }

    if (token) {
      return new AgentBoxClient({
        baseUrl: this.baseUrl.toString(),
        actor: this.token ? options.actor ?? this.actor : options.actor,
        token,
        grantToken,
        authScheme: optionalNonEmpty(options.authScheme) ?? (this.token ? this.authScheme : undefined),
        fetch: this.fetchImpl
      });
    }

    return new AgentBoxClient({
      baseUrl: this.baseUrl.toString(),
      actor: options.actor ?? this.actor,
      token: this.token,
      identityToken: this.identityToken,
      grantToken: grantToken ?? this.grantToken,
      authScheme: optionalNonEmpty(options.authScheme) ?? this.authScheme,
      fetch: this.fetchImpl
    });
  }

  private async request<T>(input: {
    method: string;
    path: string;
    query?: URLSearchParams;
    body?: unknown;
    auth?: boolean;
    options?: AgentBoxClientRequestOptions;
  }): Promise<AgentBoxResult<T>> {
    const url = new URL(trimLeadingSlash(input.path), this.baseUrl);
    if (input.query) {
      for (const [key, value] of input.query) {
        url.searchParams.append(key, value);
      }
    }

    const headers: Record<string, string> = {
      accept: "application/json"
    };

    if (input.body !== undefined) {
      headers["content-type"] = "application/json";
    }

    if (input.auth !== false) {
      const auth = this.resolveAuth(input.options);
      headers.authorization = `Bearer ${auth.authorizationToken}`;
      if (auth.actor) {
        headers["x-agentbox-actor"] = auth.actor;
      }
      if (auth.grantToken) {
        headers["x-agentbox-grant-token"] = auth.grantToken;
      }
      if (auth.authScheme) {
        headers["x-agentbox-auth-scheme"] = auth.authScheme;
      }
      if (auth.admin) {
        headers["x-agentbox-admin"] = "true";
      }
    }

    const response = await this.fetchImpl(url, {
      method: input.method,
      headers,
      body: input.body === undefined ? undefined : JSON.stringify(input.body)
    });
    const payload = await parseJsonResponse(response);

    if (!response.ok || !isSuccessPayload<T>(payload)) {
      const errorPayload = isErrorPayload(payload) ? payload : fallbackErrorPayload(response);
      throw new AgentBoxApiError({
        code: errorPayload.error.code,
        message: errorPayload.error.message,
        target: errorPayload.error.target,
        request_id: errorPayload.error.request_id,
        audit_id: errorPayload.audit_id,
        status: response.status
      });
    }

    return payload;
  }

  private resolveAuth(options: AgentBoxClientRequestOptions | undefined): {
    authorizationToken: string;
    actor?: string;
    grantToken?: string;
    authScheme?: string;
    admin?: boolean;
  } {
    const optionIdentityToken = optionalNonEmpty(options?.identityToken);
    const optionToken = optionalNonEmpty(options?.token);
    if (optionIdentityToken && optionToken) {
      throw new TypeError("AgentBoxClient token and identityToken auth modes are mutually exclusive.");
    }

    const identityToken = optionIdentityToken ?? (optionToken ? undefined : this.identityToken);
    const token = optionToken ?? (optionIdentityToken ? undefined : this.token);
    const grantToken = optionalNonEmpty(options?.grantToken) ?? this.grantToken;
    const switchesAuthMode = Boolean((optionIdentityToken && !this.identityToken) || (optionToken && !this.token));
    const actor = switchesAuthMode ? optionalNonEmpty(options?.actor) : optionalNonEmpty(options?.actor) ?? this.actor;
    const authScheme = optionalNonEmpty(options?.authScheme) ?? (switchesAuthMode ? undefined : this.authScheme);

    if (identityToken) {
      return {
        authorizationToken: identityToken,
        actor,
        grantToken,
        authScheme,
        admin: options?.admin
      };
    }

    if (!token) {
      throw new TypeError("AgentBoxClient request requires a token or identityToken.");
    }
    if (!actor) {
      throw new TypeError("AgentBoxClient request requires an actor when using token auth.");
    }

    return {
      authorizationToken: token,
      actor,
      grantToken,
      authScheme,
      admin: options?.admin
    };
  }
}

async function parseJsonResponse(response: Response): Promise<unknown> {
  const text = await response.text();
  if (!text) {
    return null;
  }

  try {
    return JSON.parse(text) as unknown;
  } catch (error) {
    throw new AgentBoxApiError({
      code: "invalid_response",
      message: "AgentBox returned a non-JSON response.",
      status: response.status
    });
  }
}

function isSuccessPayload<T>(value: unknown): value is AgentBoxResult<T> {
  return Boolean(
    value &&
      typeof value === "object" &&
      "ok" in value &&
      value.ok === true &&
      "data" in value &&
      "error" in value &&
      value.error === null
  );
}

function isErrorPayload(value: unknown): value is AgentBoxErrorResponse {
  return Boolean(
    value &&
      typeof value === "object" &&
      "ok" in value &&
      value.ok === false &&
      "error" in value &&
      value.error &&
      typeof value.error === "object" &&
      "code" in value.error &&
      "message" in value.error
  );
}

function fallbackErrorPayload(response: Response): AgentBoxErrorResponse {
  return {
    ok: false,
    data: null,
    error: {
      code: "http_error",
      message: response.statusText || `HTTP ${response.status}`
    },
    audit_id: null
  };
}

function ensureTrailingSlash(value: string): string {
  return value.endsWith("/") ? value : `${value}/`;
}

function trimLeadingSlash(value: string): string {
  return value.startsWith("/") ? value.slice(1) : value;
}

function encodePathSegment(value: string): string {
  return encodeURIComponent(value);
}

function encodeKeyPath(value: string): string {
  return value.split("/").map(encodePathSegment).join("/");
}

function safeFetch(fetchImpl: FetchLike | undefined): FetchLike {
  return (input, init) => {
    const run = fetchImpl ?? globalThis.fetch;
    return run.call(globalThis, input, init);
  };
}

function optionalNonEmpty(value: string | undefined): string | undefined {
  const normalized = value?.trim();
  return normalized || undefined;
}
