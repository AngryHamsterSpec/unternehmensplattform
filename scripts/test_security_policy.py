"""Regressionen: Ein Befund darf nur im exakt geprüften Umfang eingeordnet werden."""

import copy
import unittest
from datetime import date

from security_policy import (
    KEYCLOAK,
    MSSQL_PATH,
    NETTY_PATH,
    disposition,
    local_http_deployment,
)


class SecurityPolicyTests(unittest.TestCase):
    def setUp(self):
        self.config = {
            "services": {
                "api": {
                    "environment": {
                        "ENVIRONMENT": "demo",
                        "HTTP_DEMO_MODE": "true",
                        "PUBLIC_ORIGIN": "http://localhost:8080",
                    }
                },
                "keycloak": {
                    "image": KEYCLOAK,
                    "command": ["start", "--import-realm"],
                    "environment": {
                        "KC_DB": "postgres",
                        "KC_DB_URL": "jdbc:postgresql://postgres:5432/keycloak",
                        "KC_HTTP_ENABLED": "true",
                        "KC_HOSTNAME": "http://localhost:8080/identity",
                    },
                    "volumes": [
                        {
                            "target": "/opt/keycloak/data/import/platform-realm.json",
                            "read_only": True,
                        }
                    ],
                },
                "web": {"ports": [{"host_ip": "127.0.0.1"}]},
            }
        }
        self.finding = {
            "id": "CVE-2026-75595",
            "package": "io.netty:netty-handler",
            "installed": "4.1.136.Final",
            "path": NETTY_PATH,
        }

    def review(self, **kwargs):
        return disposition(
            self.finding,
            kwargs.get("image", KEYCLOAK),
            local_http=kwargs.get("local_http", True),
            today=kwargs.get("today", date(2026, 9, 10)),
        )

    def test_exact_demo_is_recognized(self):
        self.assertTrue(local_http_deployment(self.config))
        self.assertEqual(self.review()["status"], "not_affected_in_local_demo")

    def test_changed_deployments_fail_closed(self):
        variations = [
            ("keycloak", "ports", [{"published": "8443"}]),
            ("keycloak", "command", ["start", "--https-client-auth=required"]),
            ("keycloak", "entrypoint", ["/custom.sh"]),
            ("keycloak", "volumes", [{"target": "/opt/keycloak/conf/keycloak.conf"}]),
            ("web", "ports", [{"host_ip": "0.0.0.0"}]),
        ]
        for service, field, value in variations:
            with self.subTest(field=field, service=service):
                changed = copy.deepcopy(self.config)
                changed["services"][service][field] = value
                self.assertFalse(local_http_deployment(changed))

    def test_tls_or_java_override_fail_closed(self):
        for field in ("KC_HTTPS_CERTIFICATE_FILE", "JAVA_OPTS_APPEND"):
            changed = copy.deepcopy(self.config)
            changed["services"]["keycloak"]["environment"][field] = "changed"
            self.assertFalse(local_http_deployment(changed))

    def test_nonlocal_and_production_fail_closed(self):
        for field, value in (
            ("ENVIRONMENT", "production"),
            ("PUBLIC_ORIGIN", "https://localhost"),
            ("PUBLIC_ORIGIN", "http://example.com"),
            ("HTTP_DEMO_MODE", "false"),
        ):
            changed = copy.deepcopy(self.config)
            changed["services"]["api"]["environment"][field] = value
            self.assertFalse(local_http_deployment(changed))

    def test_missing_config_fails_closed(self):
        self.assertFalse(local_http_deployment({}))

    def test_unknown_version_path_id_package_are_never_exempt(self):
        for field in ("id", "package", "installed", "path"):
            with self.subTest(field=field):
                original = self.finding[field]
                self.finding[field] = "unknown"
                self.assertIsNone(self.review())
                self.finding[field] = original

    def test_other_image_or_expired_review_is_not_exempt(self):
        self.assertIsNone(self.review(image="other"))
        self.assertIsNone(self.review(today=date(2026, 10, 11)))

    def test_netty_requires_confirmed_demo(self):
        self.assertIsNone(self.review(local_http=False))

    def test_mssql_requires_exact_patched_artifact(self):
        self.finding = {
            "id": "CVE-2025-59250",
            "package": "com.microsoft.sqlserver:mssql-jdbc",
            "installed": "13.2.1",
            "path": MSSQL_PATH,
        }
        self.assertEqual(self.review(local_http=False)["status"], "false_positive")
        self.finding["path"] = MSSQL_PATH.replace("13.2.1", "13.2.0")
        self.assertIsNone(self.review())


if __name__ == "__main__":
    unittest.main()
