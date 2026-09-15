"""Erzeugt einmalig lokale Demo-Secrets und OIDC-Import, ohne sie auszugeben."""

import base64
import json
import secrets
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ORG_A = "10000000-0000-4000-8000-000000000001"
ORG_B = "10000000-0000-4000-8000-000000000002"
USERS = [
    ("20000000-0000-4000-8000-000000000001", "admin", "Demo Administration"),
    ("20000000-0000-4000-8000-000000000002", "analyst", "Demo Architektur"),
    ("20000000-0000-4000-8000-000000000003", "viewer", "Demo Lesekonto"),
    ("20000000-0000-4000-8000-000000000004", "mandant-b", "Demo Testmandant B"),
]


def main() -> None:
    path = ROOT / ".env"
    local = ROOT / ".local"
    local.mkdir(exist_ok=True)
    if path.exists() and "--refresh-realm" not in sys.argv:
        print(".env ist vorhanden und wird nicht überschrieben.")
        return
    values = {
        name: secrets.token_hex(32)
        for name in (
            "POSTGRES_PASSWORD",
            "PLATFORM_APP_PASSWORD",
            "PLATFORM_AUTH_PASSWORD",
            "PLATFORM_MIGRATION_PASSWORD",
            "KEYCLOAK_DB_PASSWORD",
            "OIDC_CLIENT_SECRET",
            "SESSION_SECRET",
            "DEMO_PASSWORD",
        )
    }
    values.update(
        {
            "OIDC_ENCRYPTION_KEY": base64.urlsafe_b64encode(secrets.token_bytes(32)).decode(),
            "PUBLIC_ORIGIN": "http://localhost:8080",
            "ENVIRONMENT": "demo",
            "HTTP_DEMO_MODE": "true",
            "OIDC_ISSUER": "http://localhost:8080/identity/realms/platform",
            "OPENAI_ENABLED": "false",
            "OPENAI_API_KEY": "",
            "OPENAI_MODEL": "",
            "OPENAI_PRICE_VERSION": "",
            "OPENAI_INPUT_PER_MILLION": "",
            "OPENAI_OUTPUT_PER_MILLION": "",
            "OPENAI_DAILY_BUDGET": "1.00",
            "OPENAI_ORGANIZATION_IDS": "",
        }
    )
    for name, role in (
        ("DATABASE_URL", "app"),
        ("AUTH_DATABASE_URL", "auth"),
        ("MIGRATION_DATABASE_URL", "migrator"),
    ):
        password_key = (
            "PLATFORM_MIGRATION_PASSWORD"
            if role == "migrator"
            else f"PLATFORM_{role.upper()}_PASSWORD"
        )
        values[name] = (
            f"postgresql+psycopg://platform_{role}:{values[password_key]}@postgres:5432/platform"
        )
    if path.exists():
        # Nur unsere lokale dotenv-Demo; Geheimnisse werden nicht neu erzeugt/überschrieben.
        values = dict(
            line.split("=", 1)
            for line in path.read_text(encoding="utf8").splitlines()
            if line and not line.startswith("#") and "=" in line
        )
    registry = local / "data-sources.json"
    if not registry.exists():
        with registry.open("x", encoding="utf8") as output:
            output.write("[]\n")
    realm = {
        "realm": "platform",
        "enabled": True,
        "displayName": "Unternehmensplattform · lokale Demo",
        "registrationAllowed": False,
        "resetPasswordAllowed": False,
        "loginWithEmailAllowed": False,
        "internationalizationEnabled": True,
        "supportedLocales": ["de"],
        "defaultLocale": "de",
        "bruteForceProtected": True,
        "permanentLockout": False,
        "failureFactor": 5,
        "sslRequired": "none",
        "clients": [
            {
                "clientId": "platform",
                "enabled": True,
                "protocol": "openid-connect",
                "publicClient": False,
                "secret": values["OIDC_CLIENT_SECRET"],
                "standardFlowEnabled": True,
                "directAccessGrantsEnabled": False,
                "serviceAccountsEnabled": False,
                "implicitFlowEnabled": False,
                "redirectUris": ["http://localhost:8080/api/v1/auth/callback"],
                "webOrigins": ["http://localhost:8080"],
                "attributes": {"pkce.code.challenge.method": "S256"},
                "defaultClientScopes": ["profile", "email"],
            }
        ],
        "users": [
            {
                "id": uid,
                "username": username,
                "enabled": True,
                "firstName": name,
                "lastName": "Demo",
                "emailVerified": True,
                "email": f"{username}@example.com",
                "credentials": [
                    {
                        "type": "password",
                        "value": values["DEMO_PASSWORD"],
                        "temporary": False,
                    }
                ],
            }
            for uid, username, name in USERS
        ],
    }
    # Exklusives Erstellen verhindert stilles Überschreiben bei paralleler Einrichtung.
    if not path.exists():
        with path.open("x", encoding="utf8") as output:
            output.write("\n".join(f"{k}={v}" for k, v in values.items()) + "\n")
    (local / "platform-realm.json").write_text(
        json.dumps(realm, ensure_ascii=False, indent=2), encoding="utf8"
    )
    (local / "demo-zugang.txt").write_text(
        "Nur lokale synthetische Demo. Konten: admin, analyst, viewer, mandant-b\n"
        "Gemeinsames zufälliges Demo-Passwort: " + values["DEMO_PASSWORD"] + "\n",
        encoding="utf8",
    )
    print(
        "Lokale Konfiguration erstellt. Zugangsdaten: .local/demo-zugang.txt. Keine Geheimnisse im Git."
    )


if __name__ == "__main__":
    main()
