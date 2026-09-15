#!/bin/sh
set -eu
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<'SQL'
\getenv app_password PLATFORM_APP_PASSWORD
\getenv auth_password PLATFORM_AUTH_PASSWORD
\getenv migration_password PLATFORM_MIGRATION_PASSWORD
\getenv identity_password KEYCLOAK_DB_PASSWORD
CREATE ROLE platform_migrator LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS PASSWORD :'migration_password';
CREATE ROLE platform_app LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS PASSWORD :'app_password';
CREATE ROLE platform_auth LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS PASSWORD :'auth_password';
CREATE ROLE keycloak LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS PASSWORD :'identity_password';
CREATE DATABASE platform OWNER platform_migrator;
CREATE DATABASE keycloak OWNER keycloak;
REVOKE ALL ON DATABASE platform FROM PUBLIC;
GRANT CONNECT ON DATABASE platform TO platform_migrator, platform_app, platform_auth;
REVOKE ALL ON DATABASE keycloak FROM PUBLIC;
GRANT CONNECT ON DATABASE keycloak TO keycloak;
\connect platform
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
ALTER SCHEMA public OWNER TO platform_migrator;
GRANT USAGE ON SCHEMA public TO platform_app, platform_auth;
SQL
