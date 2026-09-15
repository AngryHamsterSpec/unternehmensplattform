CREATE TABLE data_rule_sets (
 id UUID PRIMARY KEY,
 organization_id UUID NOT NULL,
 created_by_user_id UUID NOT NULL,
 name VARCHAR(160) NOT NULL,
 rules JSONB NOT NULL CHECK (jsonb_typeof(rules)='array' AND jsonb_array_length(rules) BETWEEN 1 AND 50),
 replaces_id UUID,
 created_at TIMESTAMPTZ NOT NULL,
 UNIQUE(organization_id,id),
 FOREIGN KEY(organization_id,created_by_user_id) REFERENCES organization_memberships(organization_id,user_id),
 FOREIGN KEY(organization_id,replaces_id) REFERENCES data_rule_sets(organization_id,id)
);
CREATE TABLE data_tasks (
 id UUID PRIMARY KEY,
 organization_id UUID NOT NULL,
 created_by_user_id UUID NOT NULL,
 idempotency_key UUID NOT NULL,
 dataset_id UUID,
 version_no INTEGER,
 kind VARCHAR(12) NOT NULL CHECK(kind IN ('ANALYSIS','SOURCE','PLAN')),
 request_hash VARCHAR(64) NOT NULL,
 request JSONB NOT NULL,
 status VARCHAR(12) NOT NULL DEFAULT 'QUEUED' CHECK(status IN ('QUEUED','RUNNING','SUCCEEDED','FAILED','CANCELLED')),
 lease_token UUID,
 lease_until TIMESTAMPTZ,
 attempts INTEGER NOT NULL DEFAULT 0 CHECK(attempts BETWEEN 0 AND 3),
 progress INTEGER NOT NULL DEFAULT 0 CHECK(progress BETWEEN 0 AND 100),
 message VARCHAR(160) NOT NULL,
 error VARCHAR(300),
 result JSONB,
 result_hash VARCHAR(64),
 created_at TIMESTAMPTZ NOT NULL,
 finished_at TIMESTAMPTZ,
 UNIQUE(organization_id,id),
 UNIQUE(organization_id,created_by_user_id,idempotency_key),
 FOREIGN KEY(organization_id,created_by_user_id) REFERENCES organization_memberships(organization_id,user_id),
 FOREIGN KEY(organization_id,dataset_id,version_no) REFERENCES data_versions(organization_id,dataset_id,version_no),
 CHECK((kind='SOURCE' AND dataset_id IS NULL AND version_no IS NULL) OR (kind!='SOURCE' AND dataset_id IS NOT NULL AND version_no > 0)),
 CHECK((status IN ('QUEUED','RUNNING') AND finished_at IS NULL AND error IS NULL AND result IS NULL AND result_hash IS NULL)
 OR (status='SUCCEEDED' AND finished_at IS NOT NULL AND result IS NOT NULL AND result_hash ~ '^[0-9a-f]{64}$' AND error IS NULL)
 OR (status IN ('FAILED','CANCELLED') AND finished_at IS NOT NULL AND result IS NULL AND result_hash IS NULL AND error IS NOT NULL))
);
CREATE INDEX ix_data_tasks_queue ON data_tasks(organization_id,status,created_at);
CREATE INDEX ix_data_tasks_dataset ON data_tasks(organization_id,dataset_id,created_at);
REVOKE ALL ON data_rule_sets,data_tasks FROM PUBLIC;
ALTER TABLE data_rule_sets ENABLE ROW LEVEL SECURITY;
ALTER TABLE data_rule_sets FORCE ROW LEVEL SECURITY;
ALTER TABLE data_tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE data_tasks FORCE ROW LEVEL SECURITY;
CREATE POLICY migration_access ON data_rule_sets TO platform_migrator USING(true) WITH CHECK(true);
CREATE POLICY migration_access ON data_tasks TO platform_migrator USING(true) WITH CHECK(true);
CREATE POLICY tenant_access ON data_rule_sets TO platform_app USING(organization_id=NULLIF(current_setting('app.organization_id',true),'')::uuid) WITH CHECK(organization_id=NULLIF(current_setting('app.organization_id',true),'')::uuid);
CREATE POLICY tenant_access ON data_tasks TO platform_app USING(organization_id=NULLIF(current_setting('app.organization_id',true),'')::uuid) WITH CHECK(organization_id=NULLIF(current_setting('app.organization_id',true),'')::uuid);
GRANT SELECT,INSERT ON data_rule_sets,data_tasks TO platform_app;
GRANT UPDATE(status,lease_token,lease_until,attempts,progress,message,error,result,result_hash,finished_at) ON data_tasks TO platform_app;
CREATE FUNCTION protect_finished_data_task() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF OLD.status NOT IN ('QUEUED','RUNNING') THEN RAISE EXCEPTION 'Abgeschlossene Auftraege sind unveraenderlich'; END IF;
 RETURN NEW;
END; $$;
REVOKE ALL ON FUNCTION protect_finished_data_task() FROM PUBLIC;
CREATE TRIGGER immutable_data_task BEFORE UPDATE ON data_tasks FOR EACH ROW EXECUTE FUNCTION protect_finished_data_task();
