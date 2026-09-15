
CREATE TABLE data_blobs (
	id UUID NOT NULL,
	organization_id UUID NOT NULL,
	content_hash VARCHAR(64) NOT NULL,
	content BYTEA NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (organization_id, id),
	CHECK (octet_length(content) BETWEEN 1 AND 524288),
	FOREIGN KEY(organization_id) REFERENCES organizations (id)
)

;
REVOKE ALL ON data_blobs FROM PUBLIC;
ALTER TABLE data_blobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE data_blobs FORCE ROW LEVEL SECURITY;
CREATE POLICY migration_access ON data_blobs TO platform_migrator USING (true) WITH CHECK (true);
CREATE POLICY tenant_access ON data_blobs TO platform_app USING (organization_id = NULLIF(current_setting('app.organization_id', true), '')::uuid) WITH CHECK (organization_id = NULLIF(current_setting('app.organization_id', true), '')::uuid);
GRANT SELECT, INSERT ON data_blobs TO platform_app;

CREATE TABLE datasets (
	id UUID NOT NULL,
	organization_id UUID NOT NULL,
	created_by_user_id UUID NOT NULL,
	name VARCHAR(160) NOT NULL,
	filename VARCHAR(160) NOT NULL,
	delimiter VARCHAR(1) NOT NULL,
	original_blob_id UUID NOT NULL,
	original_hash VARCHAR(64) NOT NULL,
	original_bytes INTEGER NOT NULL,
	current_version INTEGER NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (organization_id, id),
	FOREIGN KEY(organization_id, original_blob_id) REFERENCES data_blobs (organization_id, id),
	FOREIGN KEY(organization_id, created_by_user_id) REFERENCES organization_memberships (organization_id, user_id),
	CHECK (current_version >= 0),
	FOREIGN KEY(organization_id) REFERENCES organizations (id)
)

;
CREATE INDEX ix_datasets_org_created ON datasets (organization_id, created_at);
REVOKE ALL ON datasets FROM PUBLIC;
ALTER TABLE datasets ENABLE ROW LEVEL SECURITY;
ALTER TABLE datasets FORCE ROW LEVEL SECURITY;
CREATE POLICY migration_access ON datasets TO platform_migrator USING (true) WITH CHECK (true);
CREATE POLICY tenant_access ON datasets TO platform_app USING (organization_id = NULLIF(current_setting('app.organization_id', true), '')::uuid) WITH CHECK (organization_id = NULLIF(current_setting('app.organization_id', true), '')::uuid);
GRANT SELECT, INSERT ON datasets TO platform_app;

CREATE TABLE data_jobs (
	id UUID NOT NULL,
	organization_id UUID NOT NULL,
	dataset_id UUID NOT NULL,
	created_by_user_id UUID NOT NULL,
	kind VARCHAR(12) NOT NULL,
	status VARCHAR(12) NOT NULL,
	source_version INTEGER,
	steps JSONB NOT NULL,
	result_blob_id UUID,
	result_hash VARCHAR(64),
	profile JSONB,
	error VARCHAR(300),
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	finished_at TIMESTAMP WITH TIME ZONE,
	PRIMARY KEY (id),
	UNIQUE (organization_id, dataset_id, id),
	FOREIGN KEY(organization_id, dataset_id) REFERENCES datasets (organization_id, id),
	FOREIGN KEY(organization_id, created_by_user_id) REFERENCES organization_memberships (organization_id, user_id),
	FOREIGN KEY(organization_id, result_blob_id) REFERENCES data_blobs (organization_id, id),
	CHECK (kind IN ('IMPORT', 'PREVIEW')),
	CHECK (status IN ('QUEUED', 'SUCCEEDED', 'FAILED')),
	CHECK ((kind = 'IMPORT' AND source_version IS NULL) OR (kind = 'PREVIEW' AND source_version > 0)),
	CHECK ((status = 'QUEUED' AND finished_at IS NULL AND result_blob_id IS NULL AND profile IS NULL AND error IS NULL) OR (status = 'SUCCEEDED' AND finished_at IS NOT NULL AND result_blob_id IS NOT NULL AND profile IS NOT NULL AND error IS NULL) OR (status = 'FAILED' AND finished_at IS NOT NULL AND result_blob_id IS NULL AND profile IS NULL AND error IS NOT NULL)),
	FOREIGN KEY(organization_id) REFERENCES organizations (id)
)

;
CREATE INDEX ix_jobs_queue ON data_jobs (organization_id, status, created_at);
REVOKE ALL ON data_jobs FROM PUBLIC;
ALTER TABLE data_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE data_jobs FORCE ROW LEVEL SECURITY;
CREATE POLICY migration_access ON data_jobs TO platform_migrator USING (true) WITH CHECK (true);
CREATE POLICY tenant_access ON data_jobs TO platform_app USING (organization_id = NULLIF(current_setting('app.organization_id', true), '')::uuid) WITH CHECK (organization_id = NULLIF(current_setting('app.organization_id', true), '')::uuid);
GRANT SELECT, INSERT ON data_jobs TO platform_app;

CREATE TABLE data_versions (
	id UUID NOT NULL,
	organization_id UUID NOT NULL,
	dataset_id UUID NOT NULL,
	job_id UUID NOT NULL,
	blob_id UUID NOT NULL,
	created_by_user_id UUID NOT NULL,
	version_no INTEGER NOT NULL,
	source_version INTEGER,
	content_hash VARCHAR(64) NOT NULL,
	profile JSONB NOT NULL,
	steps JSONB NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (organization_id, dataset_id, version_no),
	UNIQUE (organization_id, job_id),
	FOREIGN KEY(organization_id, dataset_id) REFERENCES datasets (organization_id, id),
	FOREIGN KEY(organization_id, dataset_id, job_id) REFERENCES data_jobs (organization_id, dataset_id, id),
	FOREIGN KEY(organization_id, blob_id) REFERENCES data_blobs (organization_id, id),
	FOREIGN KEY(organization_id, created_by_user_id) REFERENCES organization_memberships (organization_id, user_id),
	CHECK (version_no > 0),
	FOREIGN KEY(organization_id) REFERENCES organizations (id)
)

;
REVOKE ALL ON data_versions FROM PUBLIC;
ALTER TABLE data_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE data_versions FORCE ROW LEVEL SECURITY;
CREATE POLICY migration_access ON data_versions TO platform_migrator USING (true) WITH CHECK (true);
CREATE POLICY tenant_access ON data_versions TO platform_app USING (organization_id = NULLIF(current_setting('app.organization_id', true), '')::uuid) WITH CHECK (organization_id = NULLIF(current_setting('app.organization_id', true), '')::uuid);
GRANT SELECT, INSERT ON data_versions TO platform_app;
GRANT UPDATE (current_version) ON datasets TO platform_app;
GRANT UPDATE (status, finished_at, error, profile, result_blob_id, result_hash) ON data_jobs TO platform_app;
CREATE FUNCTION protect_finished_data_job() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF OLD.status != 'QUEUED' THEN
        RAISE EXCEPTION 'Abgeschlossene Datenauftraege sind unveraenderlich';
    END IF;
    RETURN NEW;
END;
$$;
REVOKE ALL ON FUNCTION protect_finished_data_job() FROM PUBLIC;
CREATE TRIGGER immutable_finished_job BEFORE UPDATE ON data_jobs FOR EACH ROW EXECUTE FUNCTION protect_finished_data_job();
ALTER TABLE data_jobs ADD CONSTRAINT fk_job_source
FOREIGN KEY (organization_id, dataset_id, source_version)
REFERENCES data_versions (organization_id, dataset_id, version_no);
ALTER TABLE data_versions ADD CONSTRAINT fk_version_source
FOREIGN KEY (organization_id, dataset_id, source_version)
REFERENCES data_versions (organization_id, dataset_id, version_no);
