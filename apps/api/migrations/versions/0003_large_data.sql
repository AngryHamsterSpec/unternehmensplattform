
CREATE TABLE data_objects (
 id UUID PRIMARY KEY,
 organization_id UUID NOT NULL REFERENCES organizations(id),
 created_by_user_id UUID NOT NULL,
 kind TEXT NOT NULL CHECK (kind IN ('UPLOAD','DERIVED')),
 status TEXT NOT NULL DEFAULT 'OPEN' CHECK(status IN ('OPEN','SEALED','CANCELLED')),
 expected_bytes BIGINT NOT NULL CHECK(expected_bytes BETWEEN 0 AND 1073741824),
 received_bytes BIGINT NOT NULL DEFAULT 0 CHECK(received_bytes BETWEEN 0 AND 8589934592),
 chunk_count INTEGER NOT NULL DEFAULT 0 CHECK(chunk_count >= 0),
 content_hash VARCHAR(64),
 metadata JSONB NOT NULL DEFAULT '{}',
 created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 UNIQUE(organization_id,id),
 FOREIGN KEY(organization_id,created_by_user_id) REFERENCES organization_memberships(organization_id,user_id),
 CHECK((status='SEALED' AND content_hash ~ '^[0-9a-f]{64}$') OR (status!='SEALED' AND content_hash IS NULL)),
 CHECK(kind!='UPLOAD' OR (expected_bytes > 0 AND received_bytes <= expected_bytes))
);
CREATE TABLE data_chunks (
 organization_id UUID NOT NULL,
 object_id UUID NOT NULL,
 ordinal INTEGER NOT NULL CHECK(ordinal >= 0),
 content BYTEA NOT NULL CHECK(octet_length(content) BETWEEN 1 AND 4194304),
 content_hash VARCHAR(64) NOT NULL CHECK(content_hash ~ '^[0-9a-f]{64}$'),
 row_start BIGINT,
 row_count INTEGER,
 PRIMARY KEY(organization_id,object_id,ordinal),
 FOREIGN KEY(organization_id,object_id) REFERENCES data_objects(organization_id,id),
 CHECK((row_start IS NULL AND row_count IS NULL) OR (row_start >= 0 AND row_count >= 0))
);
CREATE INDEX ix_data_chunks_rows ON data_chunks(organization_id,object_id,row_start);
REVOKE ALL ON data_objects,data_chunks FROM PUBLIC;
ALTER TABLE data_objects ENABLE ROW LEVEL SECURITY;
ALTER TABLE data_objects FORCE ROW LEVEL SECURITY;
ALTER TABLE data_chunks ENABLE ROW LEVEL SECURITY;
ALTER TABLE data_chunks FORCE ROW LEVEL SECURITY;
CREATE POLICY migration_access ON data_objects TO platform_migrator USING(true) WITH CHECK(true);
CREATE POLICY migration_access ON data_chunks TO platform_migrator USING(true) WITH CHECK(true);
CREATE POLICY tenant_access ON data_objects TO platform_app USING(organization_id=NULLIF(current_setting('app.organization_id',true),'')::uuid) WITH CHECK(organization_id=NULLIF(current_setting('app.organization_id',true),'')::uuid);
CREATE POLICY tenant_access ON data_chunks TO platform_app USING(organization_id=NULLIF(current_setting('app.organization_id',true),'')::uuid) WITH CHECK(organization_id=NULLIF(current_setting('app.organization_id',true),'')::uuid);
GRANT SELECT,INSERT ON data_objects,data_chunks TO platform_app;
GRANT DELETE ON data_chunks TO platform_app;
GRANT UPDATE(status,received_bytes,chunk_count,content_hash) ON data_objects TO platform_app;
CREATE FUNCTION protect_data_object() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF OLD.status != 'OPEN' THEN RAISE EXCEPTION 'Abgeschlossene Speicherobjekte sind unveraenderlich'; END IF;
 RETURN NEW;
END; $$;
REVOKE ALL ON FUNCTION protect_data_object() FROM PUBLIC;
CREATE TRIGGER immutable_data_object BEFORE UPDATE ON data_objects FOR EACH ROW EXECUTE FUNCTION protect_data_object();
CREATE FUNCTION protect_data_chunk() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE state TEXT;
BEGIN
 IF TG_OP = 'INSERT' THEN
   SELECT status INTO state FROM data_objects WHERE organization_id=NEW.organization_id AND id=NEW.object_id FOR UPDATE;
 ELSE
   SELECT status INTO state FROM data_objects WHERE organization_id=OLD.organization_id AND id=OLD.object_id FOR UPDATE;
 END IF;
 IF state IS DISTINCT FROM 'OPEN' THEN RAISE EXCEPTION 'Speicherabschnitte sind unveraenderlich'; END IF;
 IF TG_OP = 'DELETE' THEN RETURN OLD; END IF;
 RETURN NEW;
END; $$;
REVOKE ALL ON FUNCTION protect_data_chunk() FROM PUBLIC;
CREATE TRIGGER immutable_data_chunk BEFORE INSERT OR DELETE ON data_chunks FOR EACH ROW EXECUTE FUNCTION protect_data_chunk();
ALTER TABLE data_blobs ALTER COLUMN content DROP NOT NULL;
ALTER TABLE data_blobs ADD COLUMN object_id UUID;
ALTER TABLE data_blobs ADD COLUMN storage_meta JSONB NOT NULL DEFAULT '{}';
ALTER TABLE data_blobs ADD CONSTRAINT fk_blob_object FOREIGN KEY(organization_id,object_id) REFERENCES data_objects(organization_id,id);
ALTER TABLE data_blobs ADD CONSTRAINT blob_storage CHECK ((content IS NOT NULL AND object_id IS NULL) OR (content IS NULL AND object_id IS NOT NULL));
CREATE FUNCTION validate_sealed_blob() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF NEW.object_id IS NOT NULL AND NOT EXISTS (
 SELECT 1 FROM data_objects WHERE id=NEW.object_id AND organization_id=NEW.organization_id AND status='SEALED' AND content_hash=NEW.content_hash
 ) THEN RAISE EXCEPTION 'Speicherobjekt ist nicht versiegelt'; END IF;
 RETURN NEW;
END; $$;
REVOKE ALL ON FUNCTION validate_sealed_blob() FROM PUBLIC;
CREATE TRIGGER sealed_blob BEFORE INSERT ON data_blobs FOR EACH ROW EXECUTE FUNCTION validate_sealed_blob();
ALTER TABLE data_jobs ADD COLUMN processing_mode TEXT NOT NULL DEFAULT 'LEGACY' CHECK(processing_mode IN ('LEGACY','STREAM'));
ALTER TABLE data_jobs ADD COLUMN lease_token UUID;
ALTER TABLE data_jobs ADD COLUMN lease_until TIMESTAMPTZ;
ALTER TABLE data_jobs ADD COLUMN attempts INTEGER NOT NULL DEFAULT 0;
ALTER TABLE data_jobs ADD COLUMN progress INTEGER NOT NULL DEFAULT 0 CHECK(progress BETWEEN 0 AND 100);
ALTER TABLE data_jobs ADD COLUMN progress_message VARCHAR(160) NOT NULL DEFAULT '';
ALTER TABLE data_jobs ADD COLUMN processed_rows BIGINT NOT NULL DEFAULT 0 CHECK(processed_rows >= 0);
DO $$
DECLARE item RECORD;
BEGIN
 FOR item IN SELECT conname FROM pg_constraint WHERE conrelid='data_jobs'::regclass AND contype='c' AND strpos(pg_get_constraintdef(oid),'status') > 0 LOOP
 EXECUTE 'ALTER TABLE data_jobs DROP CONSTRAINT ' || quote_ident(item.conname);
 END LOOP;
END; $$;
ALTER TABLE data_jobs ADD CONSTRAINT job_status CHECK(status IN ('QUEUED','RUNNING','SUCCEEDED','FAILED','CANCELLED'));
ALTER TABLE data_jobs ADD CONSTRAINT job_result CHECK(
 (status IN ('QUEUED','RUNNING') AND finished_at IS NULL AND result_blob_id IS NULL AND profile IS NULL AND error IS NULL)
 OR (status='SUCCEEDED' AND finished_at IS NOT NULL AND result_blob_id IS NOT NULL AND profile IS NOT NULL AND error IS NULL)
 OR (status IN ('FAILED','CANCELLED') AND finished_at IS NOT NULL AND result_blob_id IS NULL AND profile IS NULL AND error IS NOT NULL)
);
ALTER TABLE data_jobs ADD CONSTRAINT running_lease CHECK(status!='RUNNING' OR (processing_mode='STREAM' AND lease_token IS NOT NULL AND lease_until IS NOT NULL));
GRANT UPDATE(lease_token,lease_until,attempts,progress,progress_message,processed_rows) ON data_jobs TO platform_app;
CREATE OR REPLACE FUNCTION protect_finished_data_job() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF OLD.status NOT IN ('QUEUED','RUNNING') THEN RAISE EXCEPTION 'Abgeschlossene Datenauftraege sind unveraenderlich'; END IF;
 RETURN NEW;
END; $$;
