"""Unitkonfiguration ohne lokale oder echte Zugangsdaten."""

import os

from cryptography.fernet import Fernet

# Docker-Integration liefert explizite Werte; Unitprüfungen brauchen synthetische Konfiguration.
if os.environ.get("RUN_DB_TESTS") != "1":
    os.environ["ENVIRONMENT"] = "test"
    os.environ["PUBLIC_ORIGIN"] = "http://localhost:8080"
    os.environ["HTTP_DEMO_MODE"] = "true"
    os.environ["OIDC_ISSUER"] = "http://localhost:8080/identity/realms/platform"
    os.environ["OIDC_CLIENT_SECRET"] = "unit-test-client-secret-" * 2
    os.environ["SESSION_SECRET"] = "unit-test-session-secret-" * 2
    os.environ["OIDC_ENCRYPTION_KEY"] = Fernet.generate_key().decode()
    os.environ["OPENAI_ENABLED"] = "false"
