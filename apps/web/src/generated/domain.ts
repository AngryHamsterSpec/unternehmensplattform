// Automatisch erzeugt: python scripts/generate_contracts.py. Nicht manuell bearbeiten.
export type AnalysisInput = {
  version_no: number;
  numeric_columns: Array<string>;
  date_column: string | null;
  time_metric: string | null;
  time_grain: 'day' | 'month';
  ruleset_id: string | null;
  rules: Array<QualityRule>;
};
export type AnalysisResult = {
  engine_version: string;
  profile: DataProfile;
  options: AnalysisInput;
  numeric: Array<NumericStatistics>;
  correlations: Array<Correlation>;
  rules: Array<RuleResult>;
  score: string | null;
  score_method: string;
  time_series: TimeSeries;
  notes: Array<string>;
  ruleset: RuleSetReference | null;
  dataset_id: string;
  version_no: number;
  content_hash: string;
  original_hash: string;
};
export type AssessmentOptions = {
  weight_profile: 'ECONOMIC' | 'PERFORMANCE' | 'CUSTOM';
  custom_weights: Record<
    'cost' | 'performance' | 'resilience' | 'operations' | 'governance',
    string
  > | null;
  horizon_months: number;
  valuation_date: string;
};
export type AssessmentResult = {
  status: 'VERIFIED' | 'INCOMPLETE' | 'NO_FEASIBLE_OPTION' | 'VERIFICATION_FAILED';
  candidates: Array<CandidateResult>;
  recommended_candidate_key: 'SAAS' | 'PAAS' | 'IAAS' | 'HYBRID' | null;
  weights: Record<'cost' | 'performance' | 'resilience' | 'operations' | 'governance', string>;
  horizon_months: number;
  verification: VerificationResult;
  sensitivity: SensitivityResult;
  rule_set_version: string;
  candidate_catalog_version: string;
  cost_catalog_version: string;
  evidence: Array<Evidence>;
  assumptions: Array<string>;
  uncertainties: Array<string>;
  explanation: string;
};
export type CandidateResult = {
  key: 'SAAS' | 'PAAS' | 'IAAS' | 'HYBRID';
  label: string;
  status: 'ELIGIBLE' | 'INDETERMINATE' | 'EXCLUDED';
  score: string | null;
  rank: number | null;
  assignments: Array<WorkloadAssignment>;
  criterion_scores: Record<
    'cost' | 'performance' | 'resilience' | 'operations' | 'governance',
    string | null
  >;
  constraints: Array<Constraint>;
  costs: CostResult;
  evidence_ids: Array<string>;
  assumptions: Array<string>;
  uncertainties: Array<string>;
  explanation: string;
};
export type ChartRow = { row_number: number; values: Array<string> };
export type ChartSample = {
  version_no: number;
  content_hash: string;
  total_rows: number;
  columns: Array<string>;
  rows: Array<ChartRow>;
  method: 'complete' | 'systematic-chunks-v1';
  truncated_cells: number;
};
export type ColumnProfile = {
  name: string;
  inferred_type: 'empty' | 'decimal' | 'boolean' | 'date' | 'text';
  missing: number;
  distinct: number;
  top_values: Array<Frequency>;
  minimum: string | null;
  maximum: string | null;
  mean: string | null;
  outliers: number | null;
};
export type CommitInput = {
  preview_id: string;
  result_hash: string;
  expected_current_version: number;
};
export type CompanyProfile = {
  industry: string;
  employee_count: number | null;
  it_staff_fte: string | null;
  monthly_budget: string | null;
  initial_budget: string | null;
  currency: 'EUR';
};
export type ComponentAssignment = {
  role: string;
  service_model: 'SAAS' | 'PAAS' | 'IAAS' | 'SELF_MANAGED';
  deployment_model: 'PUBLIC_CLOUD' | 'PRIVATE_CLOUD' | 'TRADITIONAL';
  hosting_location: 'PROVIDER' | 'ON_PREMISES' | 'COLOCATION';
};
export type Constraint = {
  key: string;
  status: 'PASS' | 'FAIL' | 'UNKNOWN';
  explanation: string;
  evidence_ids: Array<string>;
};
export type Correlation = { x: string; y: string; pairs: number; pearson: string | null };
export type CostLine = {
  id: string;
  label: string;
  category: 'CAPEX' | 'OPEX';
  recurrence: 'ONCE' | 'MONTHLY';
  quantity: string | null;
  unit_price: string | null;
  total: string | null;
  price_id: string;
  evidence_ids: Array<string>;
};
export type CostResult = {
  currency: 'EUR';
  complete: boolean;
  capex_total: string | null;
  opex_total: string | null;
  tco_total: string | null;
  startup_total: string | null;
  monthly_total: string | null;
  lines: Array<CostLine>;
};
export type CsvImportInfo = {
  delimiter: string;
  encoding: string;
  has_header: boolean;
  skipped_lines: number;
  reader_version: string;
};
export type DataProfile = {
  database_source: Record<string, unknown> | null;
  rows: number;
  columns: Array<ColumnProfile>;
  missing_cells: number;
  duplicate_rows: number;
  completeness_percent: string;
  sample: Array<Array<string>>;
  profiling_version: string;
  pipeline_version: string;
  statistics_note: string;
  import_info: CsvImportInfo | null;
  source_worksheet: number | null;
  source_table: string | null;
  source_format: 'csv' | 'json' | 'jsonl' | 'xlsx' | 'parquet' | 'sqlite';
};
export type DatasetSummary = {
  id: string;
  name: string;
  filename: string;
  current_version: number;
  created_at: string;
};
export type DatasetView = {
  id: string;
  name: string;
  filename: string;
  current_version: number;
  created_at: string;
  original_hash: string;
  original_bytes: number;
  delimiter: string;
  versions: Array<VersionView>;
  jobs: Array<JobView>;
};
export type Evidence = {
  id: string;
  kind: 'INPUT' | 'CATALOG' | 'RULE' | 'CALCULATION';
  label: string;
  source: string;
  version: string;
  value: unknown;
};
export type Frequency = { value: string; count: number };
export type ImportInput = {
  name: string;
  filename: string;
  content_base64: string;
  delimiter: ',' | ';' | '\t';
};
export type ImportOptions = {
  delimiter: 'auto' | ',' | ';' | '\t' | '|';
  encoding: 'auto' | 'utf-8-sig' | 'utf-16' | 'cp1252';
  has_header: boolean;
  worksheet: number;
  table_name: string | null;
};
export type InfrastructureAsset = {
  asset_key: string;
  name: string;
  asset_type: 'SERVER' | 'STORAGE' | 'NETWORK' | 'LICENSE' | 'OTHER';
  quantity: number;
  notes: string;
};
export type JobView = {
  id: string;
  dataset_id: string;
  kind: 'IMPORT' | 'PREVIEW';
  status: 'QUEUED' | 'RUNNING' | 'SUCCEEDED' | 'FAILED' | 'CANCELLED';
  progress: number;
  progress_message: string;
  processed_rows: number;
  import_options: ImportOptions | null;
  source_version: number | null;
  steps: Array<Step>;
  error: string | null;
  profile: DataProfile | null;
  result_hash: string | null;
  created_at: string;
  finished_at: string | null;
};
export type NumericStatistics = {
  column: string;
  count: number;
  missing: number;
  invalid: number;
  mean: string | null;
  minimum: string | null;
  q1: string | null;
  median: string | null;
  q3: string | null;
  maximum: string | null;
  sample_stddev: string | null;
  outliers: number;
  histogram: Array<number>;
};
export type PlanCandidate = {
  id: string;
  step: Step;
  reason: string;
  evidence: string;
  risk: 'MEDIUM';
};
export type PlanInput = {
  version_no: number;
  mode: 'rules' | 'openai';
  approve_external_processing: boolean;
};
export type PlanResult = {
  mode: 'rules' | 'openai';
  prompt_version: string;
  source_hash: string;
  steps: Array<Step>;
  candidates: Array<PlanCandidate>;
  facts: Record<string, number>;
  uncertainty: string;
  required_decision: string;
  trace: Array<PlanTrace>;
  reserved_usd: string;
  model: string | null;
  price_version: string | null;
  input_hash: string;
};
export type PlanTrace = { role: string; decision: string };
export type PreviewInput = { source_version: number; steps: Array<Step> };
export type QualityRule = {
  column: string;
  operation: 'required' | 'unique' | 'decimal' | 'date' | 'boolean' | 'range' | 'allowed_values';
  minimum: string | null;
  maximum: string | null;
  values: Array<string>;
};
export type Requirements = { region: string; hard_budget: boolean };
export type RuleResult = {
  rule: QualityRule;
  checked: number;
  failed: number;
  example_rows: Array<number>;
};
export type RuleSetReference = { id: string; name: string; created_at: string };
export type RuleSetView = {
  name: string;
  rules: Array<QualityRule>;
  replaces_id: string | null;
  id: string;
  created_at: string;
  created_by_user_id: string;
};
export type ScenarioInput = {
  name: string;
  company_profile: CompanyProfile;
  workloads: Array<Workload>;
  infrastructure_assets: Array<InfrastructureAsset>;
  requirements: Requirements;
};
export type SensitivityResult = {
  tested_variations: number;
  winner_changes: number;
  score_gap: string | null;
  variations: Array<SensitivityVariation>;
  explanation: string;
};
export type SensitivityVariation = {
  group: 'cost' | 'performance' | 'resilience' | 'operations' | 'governance';
  factor: string;
  winner_key: 'SAAS' | 'PAAS' | 'IAAS' | 'HYBRID' | null;
  changed: boolean;
};
export type SourceCatalog = { items: Array<SourceView>; live_ai_available: boolean };
export type SourceImportInput = { source_id: string; table: string; name: string };
export type SourceResult = {
  dataset_id: string;
  job_id: string;
  original_hash: string;
  source: Record<string, unknown>;
};
export type SourceView = {
  id: string;
  name: string;
  tables: Array<string>;
  provider: 'postgresql';
};
export type Step = {
  operation:
    'trim' | 'fill_missing' | 'lowercase' | 'uppercase' | 'drop_duplicates' | 'drop_empty_rows';
  column: string | null;
  value: string | null;
};
export type TaskSummary = {
  id: string;
  created_by_user_id: string;
  dataset_id: string | null;
  version_no: number | null;
  kind: 'ANALYSIS' | 'SOURCE' | 'PLAN';
  status: 'QUEUED' | 'RUNNING' | 'SUCCEEDED' | 'FAILED' | 'CANCELLED';
  progress: number;
  message: string;
  error: string | null;
  result_hash: string | null;
  created_at: string;
  finished_at: string | null;
};
export type TaskView = {
  id: string;
  created_by_user_id: string;
  dataset_id: string | null;
  version_no: number | null;
  kind: 'ANALYSIS' | 'SOURCE' | 'PLAN';
  status: 'QUEUED' | 'RUNNING' | 'SUCCEEDED' | 'FAILED' | 'CANCELLED';
  progress: number;
  message: string;
  error: string | null;
  result_hash: string | null;
  created_at: string;
  finished_at: string | null;
  result: AnalysisResult | PlanResult | SourceResult | null;
  request: Record<string, unknown>;
};
export type TimePeriod = {
  period: string;
  rows: number;
  valid_values: number;
  sum: string | null;
  mean: string | null;
};
export type TimeSeries = {
  column: string | null;
  metric: string | null;
  grain: 'day' | 'month';
  invalid_dates: number;
  missing_dates: number;
  invalid_or_missing_metrics: number;
  total_periods: number;
  periods: Array<TimePeriod>;
};
export type UploadInput = {
  delimiter: 'auto' | ',' | ';' | '\t' | '|';
  encoding: 'auto' | 'utf-8-sig' | 'utf-16' | 'cp1252';
  has_header: boolean;
  worksheet: number;
  table_name: string | null;
  name: string;
  filename: string;
  total_bytes: number;
};
export type UploadView = {
  table_name: string | null;
  worksheet: number;
  encoding: string;
  has_header: boolean;
  name: string;
  filename: string;
  delimiter: string;
  id: string;
  status: 'OPEN' | 'SEALED' | 'CANCELLED';
  expected_bytes: number;
  received_bytes: number;
  chunk_count: number;
  chunk_bytes: number;
};
export type VerificationResult = { valid: boolean; errors: Array<string>; checks: Array<string> };
export type VersionView = {
  version_no: number;
  source_version: number | null;
  job_id: string;
  content_hash: string;
  profile: DataProfile;
  steps: Array<Step>;
  created_at: string;
  created_by_user_id: string;
};
export type Workload = {
  workload_key: string;
  name: string;
  workload_type: 'BUSINESS_APP' | 'WEB_APP' | 'DATABASE' | 'FILE_STORAGE' | 'ANALYTICS' | 'OTHER';
  user_count: number | null;
  vcpu_count: string | null;
  memory_gib: string | null;
  storage_gib: string | null;
  max_latency_ms: string | null;
  availability_percent: string | null;
  rto_seconds: number | null;
  rpo_seconds: number | null;
  sensitivity: 'PUBLIC' | 'INTERNAL' | 'CONFIDENTIAL' | 'RESTRICTED' | null;
  internet_dependency_allowed: boolean | null;
};
export type WorkloadAssignment = {
  workload_key: string;
  service_model: 'SAAS' | 'PAAS' | 'IAAS' | 'SELF_MANAGED';
  deployment_model: 'PUBLIC_CLOUD' | 'PRIVATE_CLOUD' | 'TRADITIONAL';
  hosting_location: 'PROVIDER' | 'ON_PREMISES' | 'COLOCATION';
  components: Array<ComponentAssignment>;
  explanation: string;
  evidence_ids: Array<string>;
};
