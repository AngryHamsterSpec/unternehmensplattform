# Prüfung

test_identity_security.py prüft OIDC-, Session-, CSRF- und Konfigurationsgrenzen. test_http_boundaries.py prüft unauthentifizierte Requests und sichere Fehler. test_database_integration.py ergänzt echte Rollen/RLS, Viewerrechte, letzte Administration und Entzug einer bestehenden Mitgliedschaft. Der Playwright-Workflow in apps/web/e2e verwendet den echten Keycloak-Login; API-Integration allein beweist diesen Login nicht.

Aus dem Repositoryroot:

```sh
python -m pytest apps/api/tests -p no:cacheprovider -q
docker compose --profile test run --build --rm tests
```

DB-Prüfungen werden ohne RUN_DB_TESTS=1 ausdrücklich übersprungen. Erfolgsaussagen und offene Nachweise stehen im [Phase-1-Prüfbericht](../../../../../docs/testing/PHASE_1_REPORT.md). Der Compose-Testdienst stellt drei getrennte echte Datenbankrollen bereit.

Der vollständige Restorelauf mit python scripts/check_restore.py --full-stack prüft zusätzlich echten OIDC-Login am wiederhergestellten IdP und den unveränderten Hash einer historischen Bewertung. Die Wiederaufnahme des Originalproxies wird durch scripts/test_restore_cleanup.py auch für Fehlerfälle geprüft.
