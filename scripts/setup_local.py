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


def enabled(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


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
            "PUBLIC_DEMO_ACCESS_ENABLED": "false",
            "PUBLIC_DEMO_USERNAME": "viewer",
            "PUBLIC_DEMO_PASSWORD": "",
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

    public_demo = enabled(values.get("PUBLIC_DEMO_ACCESS_ENABLED"))
    public_demo_username = values.get("PUBLIC_DEMO_USERNAME", "viewer").strip() or "viewer"
    public_demo_password = values.get("PUBLIC_DEMO_PASSWORD", "")
    if public_demo:
        if public_demo_username != "viewer":
            raise RuntimeError("Der öffentliche Demo-Zugang ist bewusst auf das Viewer-Konto begrenzt.")
        if len(public_demo_password) < 16:
            raise RuntimeError("PUBLIC_DEMO_PASSWORD benötigt mindestens 16 Zeichen.")

    registry = local / "data-sources.json"
    if not registry.exists():
        with registry.open("x", encoding="utf8") as output:
            output.write("[]\n")

    public_origin = values.get("PUBLIC_ORIGIN", "http://localhost:8080").rstrip("/")
    viewer_password = public_demo_password if public_demo else values["DEMO_PASSWORD"]
    realm_users = []
    for uid, username, name in USERS:
        password = viewer_password if username == "viewer" else values["DEMO_PASSWORD"]
        realm_users.append(
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
                        "value": password,
                        "temporary": False,
                    }
                ],
            }
        )

    realm = {
        "realm": "platform",
        "enabled": True,
        "displayName": "Unternehmensplattform · Demo",
        "loginTheme": "platform",
        "attributes": {
            "publicDemoEnabled": "true" if public_demo else "false",
            "publicDemoUsername": public_demo_username,
            "publicDemoPassword": public_demo_password if public_demo else "",
        },
        "registrationAllowed": False,
        "resetPasswordAllowed": False,
        "loginWithEmailAllowed": False,
        "internationalizationEnabled": True,
        "supportedLocales": ["de"],
        "defaultLocale": "de",
        "bruteForceProtected": True,
        "permanentLockout": False,
        "failureFactor": 5,
        "sslRequired": "none" if enabled(values.get("HTTP_DEMO_MODE")) else "external",
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
                "redirectUris": [public_origin + "/api/v1/auth/callback"],
                "webOrigins": [public_origin],
                "attributes": {"pkce.code.challenge.method": "S256"},
                "defaultClientScopes": ["profile", "email"],
            }
        ],
        "users": realm_users,
    }
    # Exklusives Erstellen verhindert stilles Überschreiben bei paralleler Einrichtung.
    if not path.exists():
        with path.open("x", encoding="utf8") as output:
            output.write("\n".join(f"{k}={v}" for k, v in values.items()) + "\n")
    (local / "platform-realm.json").write_text(
        json.dumps(realm, ensure_ascii=False, indent=2), encoding="utf8"
    )
    access_text = (
        "Nur lokale synthetische Demo. Konten: admin, analyst, viewer, mandant-b\n"
        "Gemeinsames zufälliges Demo-Passwort: " + values["DEMO_PASSWORD"] + "\n"
    )
    if public_demo:
        access_text += (
            "Öffentlicher Recruiter-Zugang: "
            + public_demo_username
            + " / "
            + public_demo_password
            + "\n"
        )
    (local / "demo-zugang.txt").write_text(access_text, encoding="utf8")
    print(
        "Demo-Konfiguration erstellt. Zugangsdaten: .local/demo-zugang.txt. Keine Geheimnisse im Git."
    )


if __name__ == "__main__":
    main()
