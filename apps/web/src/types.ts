import type * as Domain from './generated/domain';

export type Decimal = string | null;
export type Group = 'cost' | 'performance' | 'resilience' | 'operations' | 'governance';
export type Role = 'ORG_ADMIN' | 'ARCHITECTURE_ANALYST' | 'VIEWER';
export type Plan = 'SAAS' | 'PAAS' | 'IAAS' | 'HYBRID';
export type ScenarioInput = Domain.ScenarioInput;
export type Workload = Domain.Workload;
export type Asset = Domain.InfrastructureAsset;
export type Candidate = Domain.CandidateResult;
export type Evidence = Domain.Evidence;
export type Options = Omit<Domain.AssessmentOptions, 'valuation_date'> & {
  valuation_date?: string;
};

export interface Organization {
  id: string;
  name: string;
  roles: Role[];
}
export interface Session {
  user: { id: string; display_name: string };
  organization: Organization | null;
  organizations: Organization[];
  roles: Role[];
  permissions: string[];
  csrf_token: string;
  openai_available?: boolean;
  session_expires_at: string;
}
export interface Version {
  id: string;
  version_no: number;
  data: ScenarioInput;
}
export interface Scenario {
  id: string;
  name: string;
  current_version: number;
  created_at: string;
  version: Version;
  versions: { id: string; version_no: number; created_at: string }[];
}
export interface Page<T> {
  items: T[];
  next_cursor?: string | null;
}
export type Assessment = Domain.AssessmentResult & {
  id: string;
  scenario_version_id: string;
  created_at: string;
  result_hash: string;
  options: Options;
};
export interface Member {
  user_id: string;
  display_name?: string;
  roles: Role[];
  status: 'ACTIVE' | 'REVOKED';
  revision: number;
}
export interface AuditEvent {
  id: string;
  created_at: string;
  actor_user_id: string;
  event_type: string;
  entity_type: string;
  entity_id: string | null;
  metadata: Record<string, unknown>;
}
