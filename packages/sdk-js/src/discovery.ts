import { AgentBoxClient } from "./client.js";
import { AgentBoxApiError } from "./errors.js";
import type {
  AgentBoxAgentCard,
  AgentBoxClientOptions,
  AgentBoxDiscoveredClientOptions,
  AgentBoxDiscoveryOptions,
  FetchLike,
  JsonObject
} from "./types.js";

export interface AgentBoxDiscovery {
  agentCardUrl: string;
  baseUrl: string;
  a2aUrl: string;
  restApiBaseUrl: string;
  name: string | null;
  description: string | null;
  securitySchemes: JsonObject;
  agentCard: AgentBoxAgentCard;
  createClient(options: AgentBoxDiscoveredClientOptions): AgentBoxClient;
}

export async function discoverAgentBox(options: AgentBoxDiscoveryOptions): Promise<AgentBoxDiscovery> {
  const agentCardUrl = resolveAgentCardUrl(options);
  const fetchImpl = safeFetch(options.fetch);
  const response = await fetchImpl(agentCardUrl, {
    method: "GET",
    headers: {
      accept: "application/json"
    }
  });
  const payload = await parseJsonResponse(response);

  if (!response.ok || !isAgentCard(payload)) {
    throw new AgentBoxApiError({
      code: response.ok ? "invalid_response" : "http_error",
      message: response.ok
        ? "AgentBox discovery response did not include a valid Agent Card."
        : response.statusText || `HTTP ${response.status}`,
      status: response.status
    });
  }

  const baseUrl = baseUrlFromCard(payload, agentCardUrl);
  const discoveryFetch = options.fetch;

  return {
    agentCardUrl,
    baseUrl,
    a2aUrl: payload.url,
    restApiBaseUrl: joinUrl(baseUrl, "/v1"),
    name: optionalNonEmpty(payload.name) ?? null,
    description: optionalNonEmpty(payload.description) ?? null,
    securitySchemes: isJsonObject(payload.securitySchemes) ? payload.securitySchemes : {},
    agentCard: payload,
    createClient(clientOptions: AgentBoxDiscoveredClientOptions): AgentBoxClient {
      const nextOptions: AgentBoxClientOptions = {
        ...clientOptions,
        baseUrl,
        fetch: clientOptions.fetch ?? discoveryFetch
      };
      return new AgentBoxClient(nextOptions);
    }
  };
}

function resolveAgentCardUrl(options: AgentBoxDiscoveryOptions): string {
  const agentCardUrl = optionalNonEmpty(options.agentCardUrl);
  const baseUrl = optionalNonEmpty(options.baseUrl);
  if (agentCardUrl) {
    return new URL(agentCardUrl).toString();
  }
  if (baseUrl) {
    return joinUrl(baseUrl, "/.well-known/agent-card.json");
  }
  throw new TypeError("discoverAgentBox requires baseUrl or agentCardUrl.");
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
      message: "AgentBox discovery returned a non-JSON response.",
      status: response.status
    });
  }
}

function isAgentCard(value: unknown): value is AgentBoxAgentCard {
  return Boolean(isJsonObject(value) && typeof value.url === "string" && optionalNonEmpty(value.url));
}

function baseUrlFromCard(card: AgentBoxAgentCard, agentCardUrl: string): string {
  const a2aUrl = new URL(card.url);
  if (a2aUrl.pathname.replace(/\/+$/, "") === "/a2a") {
    a2aUrl.pathname = "/";
    a2aUrl.search = "";
    a2aUrl.hash = "";
    return stripTrailingSlash(a2aUrl.toString());
  }

  const cardUrl = new URL(agentCardUrl);
  cardUrl.pathname = "/";
  cardUrl.search = "";
  cardUrl.hash = "";
  return stripTrailingSlash(cardUrl.toString());
}

function isJsonObject(value: unknown): value is JsonObject {
  return Boolean(value && typeof value === "object" && !Array.isArray(value));
}

function joinUrl(baseUrl: string, path: string): string {
  return `${stripTrailingSlash(baseUrl)}/${path.replace(/^\/+/, "")}`;
}

function stripTrailingSlash(value: string): string {
  return value.replace(/\/+$/, "");
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
