export interface AgentBoxApiErrorDetails {
  code: string;
  message: string;
  target?: string;
  request_id?: string;
  audit_id?: string | null;
  status: number;
}

export class AgentBoxApiError extends Error {
  readonly code: string;
  readonly target?: string;
  readonly request_id?: string;
  readonly audit_id?: string | null;
  readonly status: number;

  constructor(details: AgentBoxApiErrorDetails) {
    super(details.message);
    this.name = "AgentBoxApiError";
    this.code = details.code;
    this.target = details.target;
    this.request_id = details.request_id;
    this.audit_id = details.audit_id;
    this.status = details.status;
  }
}

export function isAgentBoxApiError(error: unknown): error is AgentBoxApiError {
  return error instanceof AgentBoxApiError;
}
