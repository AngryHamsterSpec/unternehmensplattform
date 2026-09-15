ALTER TABLE datasets ALTER COLUMN delimiter TYPE VARCHAR(4);
ALTER TABLE data_jobs ADD COLUMN import_options JSONB NOT NULL DEFAULT '{}';
ALTER TABLE data_jobs ADD CONSTRAINT import_options_object CHECK(jsonb_typeof(import_options) = 'object');
-- Absichtlich kein UPDATE-Recht auf import_options: jeder Versuch bewahrt seine Auswahl.
