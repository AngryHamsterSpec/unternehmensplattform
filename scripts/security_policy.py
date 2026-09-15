"""Eng begrenzte, befristete Befundprüfung; Rohfunde bleiben unverändert."""

from datetime import date
from urllib.parse import urlsplit

KEYCLOAK = "quay.io/keycloak/keycloak:26.7.3@sha256:ff4257d0d64efbe99ed1ddfaf07765cc3c36dc7518bf8324d41961327f441c54"
NETTY_PATH = "opt/keycloak/lib/lib/main/io.netty.netty-handler-4.1.136.Final.jar"
MSSQL_PATH = "opt/keycloak/lib/lib/main/com.microsoft.sqlserver.mssql-jdbc-13.2.1.jre11.jar"


def local_http_deployment(config):
    """Unbekannte Konfigurationen erhalten keine Nichtbetroffenheitsannahme."""
    services = config.get("services", {})
    api = services.get("api", {}).get("environment", {})
    kc = services.get("keycloak", {})
    env = kc.get("environment", {})
    try:
        origin = urlsplit(api.get("PUBLIC_ORIGIN", ""))
    except ValueError:
        return False
    allowed = {
        "KC_DB",
        "KC_DB_URL",
        "KC_DB_USERNAME",
        "KC_DB_PASSWORD",
        "KC_HOSTNAME",
        "KC_HTTP_ENABLED",
        "KC_HTTP_RELATIVE_PATH",
        "KC_PROXY_HEADERS",
        "KC_HEALTH_ENABLED",
        "KC_LOG_LEVEL",
    }
    volumes = kc.get("volumes", [])
    ports = services.get("web", {}).get("ports", [])
    return (
        api.get("ENVIRONMENT") in {"demo", "test"}
        and str(api.get("HTTP_DEMO_MODE")).lower() == "true"
        and origin.scheme == "http"
        and origin.hostname in {"localhost", "127.0.0.1", "::1"}
        and kc.get("image") == KEYCLOAK
        and kc.get("command") == ["start", "--import-realm"]
        and not kc.get("entrypoint")
        and not kc.get("ports")
        and not kc.get("configs")
        and not kc.get("secrets")
        and not kc.get("network_mode")
        and set(env) <= allowed
        and env.get("KC_DB") == "postgres"
        and env.get("KC_DB_URL") == "jdbc:postgresql://postgres:5432/keycloak"
        and str(env.get("KC_HTTP_ENABLED")).lower() == "true"
        and env.get("KC_HOSTNAME") == api.get("PUBLIC_ORIGIN") + "/identity"
        and len(volumes) == 1
        and volumes[0].get("target") == "/opt/keycloak/data/import/platform-realm.json"
        and volumes[0].get("read_only") is True
        and bool(ports)
        and all(p.get("host_ip") in {"127.0.0.1", "::1"} for p in ports)
    )


def disposition(finding, image, *, local_http, today):
    if image != KEYCLOAK or today > date(2026, 10, 10):
        return None
    signature = (
        finding.get("id"),
        finding.get("package"),
        finding.get("installed"),
        finding.get("path"),
    )
    if signature == (
        "CVE-2025-59250",
        "com.microsoft.sqlserver:mssql-jdbc",
        "13.2.1",
        MSSQL_PATH,
    ):
        return {
            "status": "false_positive",
            "reason": "Exakte 13.2.1.jre11-JAR enthält den Herstellerfix; Scanner normalisiert das Versionssuffix.",
            "source": "https://github.com/microsoft/mssql-jdbc/releases/tag/v13.2.1",
            "expires": "2026-10-10",
        }
    if (
        signature == ("CVE-2026-75595", "io.netty:netty-handler", "4.1.136.Final", NETTY_PATH)
        and local_http
    ):
        return {
            "status": "not_affected_in_local_demo",
            "reason": "Kein TLS/SNI/mTLS-Eingang im geprüften Keycloak-HTTP-Demoprofil; verwundbare Bibliothek bleibt inventarisiert.",
            "source": "https://github.com/netty/netty/security/advisories/GHSA-c4c3-7fpv-j4q5",
            "expires": "2026-10-10",
        }
    return None
