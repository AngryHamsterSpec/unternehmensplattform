
CREATE TABLE oidc_login_attempts (
	id UUID NOT NULL,
	state_hash BYTEA NOT NULL,
	nonce_hash BYTEA NOT NULL,
	browser_binding_hash BYTEA NOT NULL,
	pkce_verifier_ciphertext BYTEA NOT NULL,
	encryption_key_id VARCHAR(80) NOT NULL,
	return_path VARCHAR(512) NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
	consumed_at TIMESTAMP WITH TIME ZONE,
	PRIMARY KEY (id),
	CONSTRAINT ck_login_state_hash CHECK (octet_length(state_hash) = 32),
	CONSTRAINT ck_login_nonce_hash CHECK (octet_length(nonce_hash) = 32),
	CONSTRAINT ck_login_browser_hash CHECK (octet_length(browser_binding_hash) = 32),
	CONSTRAINT ck_login_expiry CHECK (expires_at > created_at),
	UNIQUE (state_hash)
)

;
CREATE INDEX ix_login_attempt_expiry ON oidc_login_attempts (expires_at);

CREATE TABLE organizations (
	id UUID NOT NULL,
	name VARCHAR(200) NOT NULL,
	slug VARCHAR(80) NOT NULL,
	status VARCHAR(20) NOT NULL,
	revision INTEGER NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT ck_org_status CHECK (status IN ('ACTIVE','SUSPENDED','ARCHIVED')),
	CONSTRAINT ck_org_revision CHECK (revision > 0),
	UNIQUE (slug)
)

;

CREATE TABLE users (
	id UUID NOT NULL,
	oidc_issuer VARCHAR(512) NOT NULL,
	oidc_subject VARCHAR(255) NOT NULL,
	display_name VARCHAR(200),
	email VARCHAR(320),
	status VARCHAR(20) NOT NULL,
	auth_epoch INTEGER NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_user_oidc_identity UNIQUE (oidc_issuer, oidc_subject),
	CONSTRAINT ck_user_status CHECK (status IN ('ACTIVE','DISABLED','PSEUDONYMIZED')),
	CONSTRAINT ck_user_auth_epoch CHECK (auth_epoch >= 0)
)

;

CREATE TABLE auth_events (
	id UUID NOT NULL,
	occurred_at TIMESTAMP WITH TIME ZONE NOT NULL,
	event_type VARCHAR(80) NOT NULL,
	outcome VARCHAR(12) NOT NULL,
	user_id UUID,
	organization_id UUID,
	session_id UUID,
	request_id UUID NOT NULL,
	reason_code VARCHAR(80),
	metadata JSONB NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT ck_auth_event_outcome CHECK (outcome IN ('SUCCESS','DENIED','ERROR')),
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE RESTRICT,
	FOREIGN KEY(organization_id) REFERENCES organizations (id) ON DELETE RESTRICT
)

;
CREATE INDEX ix_auth_events_org ON auth_events (organization_id);
CREATE INDEX ix_auth_events_time_id ON auth_events (occurred_at, id);
CREATE INDEX ix_auth_events_user_time ON auth_events (user_id, occurred_at);

CREATE TABLE cost_catalog_versions (
	id UUID NOT NULL,
	organization_id UUID NOT NULL,
	version VARCHAR(100) NOT NULL,
	content_hash VARCHAR(64) NOT NULL,
	data JSONB NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (organization_id, id),
	UNIQUE (organization_id, version),
	FOREIGN KEY(organization_id) REFERENCES organizations (id)
)

;

CREATE TABLE organization_memberships (
	organization_id UUID NOT NULL,
	user_id UUID NOT NULL,
	status VARCHAR(20) NOT NULL,
	joined_at TIMESTAMP WITH TIME ZONE NOT NULL,
	revoked_at TIMESTAMP WITH TIME ZONE,
	revision INTEGER NOT NULL,
	PRIMARY KEY (organization_id, user_id),
	CONSTRAINT ck_membership_status CHECK (status IN ('ACTIVE','REVOKED')),
	CONSTRAINT ck_membership_revocation CHECK ((status = 'REVOKED' AND revoked_at IS NOT NULL) OR (status = 'ACTIVE' AND revoked_at IS NULL)),
	CONSTRAINT ck_membership_revision CHECK (revision > 0),
	FOREIGN KEY(organization_id) REFERENCES organizations (id) ON DELETE RESTRICT,
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE RESTRICT
)

;
CREATE INDEX ix_memberships_user_status_org ON organization_memberships (user_id, status, organization_id);

CREATE TABLE provider_budget_days (
	organization_id UUID NOT NULL,
	budget_date DATE NOT NULL,
	reserved_usd NUMERIC(20, 8) NOT NULL,
	PRIMARY KEY (organization_id, budget_date),
	CHECK (reserved_usd >= 0),
	FOREIGN KEY(organization_id) REFERENCES organizations (id)
)

;

CREATE TABLE audit_events (
	id UUID NOT NULL,
	organization_id UUID NOT NULL,
	actor_user_id UUID NOT NULL,
	event_type VARCHAR(100) NOT NULL,
	entity_type VARCHAR(80) NOT NULL,
	entity_id UUID,
	request_id UUID NOT NULL,
	metadata JSONB NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(organization_id, actor_user_id) REFERENCES organization_memberships (organization_id, user_id),
	FOREIGN KEY(organization_id) REFERENCES organizations (id)
)

;
CREATE INDEX ix_audit_org_time ON audit_events (organization_id, created_at, id);

CREATE TABLE auth_sessions (
	id UUID NOT NULL,
	session_token_hash BYTEA NOT NULL,
	user_id UUID NOT NULL,
	active_organization_id UUID,
	csrf_secret_hash BYTEA NOT NULL,
	auth_epoch INTEGER NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	last_seen_at TIMESTAMP WITH TIME ZONE NOT NULL,
	idle_expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
	absolute_expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
	revoked_at TIMESTAMP WITH TIME ZONE,
	PRIMARY KEY (id),
	FOREIGN KEY(active_organization_id, user_id) REFERENCES organization_memberships (organization_id, user_id) ON DELETE RESTRICT,
	CONSTRAINT ck_session_hash CHECK (octet_length(session_token_hash) = 32),
	CONSTRAINT ck_csrf_hash CHECK (octet_length(csrf_secret_hash) = 32),
	CONSTRAINT ck_session_auth_epoch CHECK (auth_epoch >= 0),
	CONSTRAINT ck_session_times CHECK (created_at <= last_seen_at AND last_seen_at <= absolute_expires_at AND idle_expires_at <= absolute_expires_at),
	UNIQUE (session_token_hash),
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE RESTRICT
)

;
CREATE INDEX ix_sessions_absolute_expiry ON auth_sessions (absolute_expires_at);
CREATE INDEX ix_sessions_org_user ON auth_sessions (active_organization_id, user_id);
CREATE INDEX ix_sessions_user_revoked ON auth_sessions (user_id, revoked_at);

CREATE TABLE company_profiles (
	id UUID NOT NULL,
	organization_id UUID NOT NULL,
	created_by_user_id UUID NOT NULL,
	name VARCHAR(160) NOT NULL,
	revision INTEGER NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (organization_id, id),
	FOREIGN KEY(organization_id, created_by_user_id) REFERENCES organization_memberships (organization_id, user_id),
	CHECK (revision > 0),
	FOREIGN KEY(organization_id) REFERENCES organizations (id)
)

;
CREATE INDEX ix_profiles_org_created ON company_profiles (organization_id, created_at, id);

CREATE TABLE membership_roles (
	organization_id UUID NOT NULL,
	user_id UUID NOT NULL,
	role_code VARCHAR(40) NOT NULL,
	granted_at TIMESTAMP WITH TIME ZONE NOT NULL,
	granted_by_user_id UUID,
	grant_actor_type VARCHAR(10) NOT NULL,
	PRIMARY KEY (organization_id, user_id, role_code),
	FOREIGN KEY(organization_id, user_id) REFERENCES organization_memberships (organization_id, user_id) ON DELETE RESTRICT,
	FOREIGN KEY(organization_id, granted_by_user_id) REFERENCES organization_memberships (organization_id, user_id) ON DELETE RESTRICT,
	CONSTRAINT ck_role_code CHECK (role_code IN ('ORG_ADMIN','ARCHITECTURE_ANALYST','VIEWER')),
	CONSTRAINT ck_role_grant_actor CHECK ((grant_actor_type = 'USER' AND granted_by_user_id IS NOT NULL) OR (grant_actor_type = 'SYSTEM' AND granted_by_user_id IS NULL))
)

;
CREATE INDEX ix_roles_grantor ON membership_roles (organization_id, granted_by_user_id);

CREATE TABLE company_profile_versions (
	id UUID NOT NULL,
	organization_id UUID NOT NULL,
	company_profile_id UUID NOT NULL,
	created_by_user_id UUID NOT NULL,
	version_no INTEGER NOT NULL,
	industry VARCHAR(120) NOT NULL,
	employee_count INTEGER,
	monthly_budget NUMERIC(20, 6),
	content_hash VARCHAR(64) NOT NULL,
	data JSONB NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (organization_id, id),
	UNIQUE (organization_id, company_profile_id, version_no),
	FOREIGN KEY(organization_id, company_profile_id) REFERENCES company_profiles (organization_id, id),
	FOREIGN KEY(organization_id, created_by_user_id) REFERENCES organization_memberships (organization_id, user_id),
	CHECK (version_no > 0),
	CHECK (monthly_budget IS NULL OR monthly_budget >= 0),
	FOREIGN KEY(organization_id) REFERENCES organizations (id)
)

;

CREATE TABLE assessments (
	id UUID NOT NULL,
	organization_id UUID NOT NULL,
	created_by_user_id UUID NOT NULL,
	profile_version_id UUID NOT NULL,
	catalog_version_id UUID NOT NULL,
	idempotency_key UUID NOT NULL,
	request_hash VARCHAR(64) NOT NULL,
	result_hash VARCHAR(64) NOT NULL,
	status VARCHAR(40) NOT NULL,
	options JSONB NOT NULL,
	input_snapshot JSONB NOT NULL,
	result JSONB NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (organization_id, id),
	UNIQUE (organization_id, created_by_user_id, idempotency_key),
	FOREIGN KEY(organization_id, profile_version_id) REFERENCES company_profile_versions (organization_id, id),
	FOREIGN KEY(organization_id, catalog_version_id) REFERENCES cost_catalog_versions (organization_id, id),
	FOREIGN KEY(organization_id, created_by_user_id) REFERENCES organization_memberships (organization_id, user_id),
	CHECK (status IN ('VERIFIED','INCOMPLETE','NO_FEASIBLE_OPTION','VERIFICATION_FAILED')),
	FOREIGN KEY(organization_id) REFERENCES organizations (id)
)

;
CREATE INDEX ix_assessment_org_created ON assessments (organization_id, created_at, id);

CREATE TABLE infrastructure_assets (
	id UUID NOT NULL,
	organization_id UUID NOT NULL,
	profile_version_id UUID NOT NULL,
	asset_key VARCHAR(64) NOT NULL,
	asset_type VARCHAR(30) NOT NULL,
	data JSONB NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (organization_id, profile_version_id, asset_key),
	FOREIGN KEY(organization_id, profile_version_id) REFERENCES company_profile_versions (organization_id, id),
	FOREIGN KEY(organization_id) REFERENCES organizations (id)
)

;

CREATE TABLE workloads (
	id UUID NOT NULL,
	organization_id UUID NOT NULL,
	profile_version_id UUID NOT NULL,
	workload_key VARCHAR(64) NOT NULL,
	name VARCHAR(160) NOT NULL,
	workload_type VARCHAR(30) NOT NULL,
	data JSONB NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (organization_id, profile_version_id, workload_key),
	FOREIGN KEY(organization_id, profile_version_id) REFERENCES company_profile_versions (organization_id, id),
	FOREIGN KEY(organization_id) REFERENCES organizations (id)
)

;

CREATE TABLE agent_runs (
	id UUID NOT NULL,
	organization_id UUID NOT NULL,
	assessment_id UUID NOT NULL,
	agent_key VARCHAR(80) NOT NULL,
	status VARCHAR(30) NOT NULL,
	data JSONB NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(organization_id, assessment_id) REFERENCES assessments (organization_id, id),
	FOREIGN KEY(organization_id) REFERENCES organizations (id)
)

;
CREATE INDEX ix_runs_assessment ON agent_runs (organization_id, assessment_id);

CREATE TABLE architecture_candidates (
	id UUID NOT NULL,
	organization_id UUID NOT NULL,
	assessment_id UUID NOT NULL,
	candidate_key VARCHAR(40) NOT NULL,
	status VARCHAR(30) NOT NULL,
	score NUMERIC(12, 6),
	rank INTEGER,
	tco_total NUMERIC(20, 6),
	PRIMARY KEY (id),
	UNIQUE (organization_id, assessment_id, id),
	UNIQUE (organization_id, assessment_id, candidate_key),
	FOREIGN KEY(organization_id, assessment_id) REFERENCES assessments (organization_id, id),
	CHECK (score IS NULL OR (score >= 0 AND score <= 100)),
	CHECK (status IN ('ELIGIBLE','INDETERMINATE','EXCLUDED')),
	FOREIGN KEY(organization_id) REFERENCES organizations (id)
)

;

CREATE TABLE explanation_requests (
	id UUID NOT NULL,
	organization_id UUID NOT NULL,
	assessment_id UUID NOT NULL,
	created_by_user_id UUID NOT NULL,
	idempotency_key UUID NOT NULL,
	status VARCHAR(20) NOT NULL,
	request_hash VARCHAR(64) NOT NULL,
	model VARCHAR(160) NOT NULL,
	price_version VARCHAR(160) NOT NULL,
	reserved_usd NUMERIC(20, 8) NOT NULL,
	input_hash VARCHAR(64) NOT NULL,
	output JSONB,
	failure_code VARCHAR(80),
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	finished_at TIMESTAMP WITH TIME ZONE,
	PRIMARY KEY (id),
	FOREIGN KEY(organization_id, assessment_id) REFERENCES assessments (organization_id, id),
	FOREIGN KEY(organization_id, created_by_user_id) REFERENCES organization_memberships (organization_id, user_id),
	UNIQUE (organization_id, created_by_user_id, idempotency_key),
	CHECK (status IN ('RESERVED','SUCCEEDED','FAILED')),
	CHECK (reserved_usd >= 0),
	FOREIGN KEY(organization_id) REFERENCES organizations (id)
)

;

CREATE TABLE cost_estimate_lines (
	id UUID NOT NULL,
	organization_id UUID NOT NULL,
	assessment_id UUID NOT NULL,
	candidate_id UUID NOT NULL,
	label VARCHAR(300) NOT NULL,
	category VARCHAR(10) NOT NULL,
	total NUMERIC(20, 6),
	data JSONB NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(organization_id, assessment_id, candidate_id) REFERENCES architecture_candidates (organization_id, assessment_id, id),
	CHECK (total IS NULL OR total >= 0),
	FOREIGN KEY(organization_id) REFERENCES organizations (id)
)

;
CREATE INDEX ix_lines_candidate ON cost_estimate_lines (organization_id, assessment_id, candidate_id);
