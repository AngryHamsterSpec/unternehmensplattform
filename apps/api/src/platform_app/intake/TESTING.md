# Prüfung

Die Domänen-/Regressionstests prüfen Grenzwerte und unbekannte Pflichtwerte. ScenarioForm.test.tsx prüft die tatsächliche Formularserialisierung einschließlich CSRF und Konflikten mit einem HTTP-Test-Double. Die DB-Integration prüft alte Versionen, Revisionskonflikte, zusammengesetzte Fremdschlüssel und Rollback samt Audit.

Aus dem Repositoryroot:

```sh
python -m pytest apps/api/tests -p no:cacheprovider -q
docker compose --profile test run --build --rm tests
```

DB-Prüfungen werden ohne RUN_DB_TESTS=1 ausdrücklich übersprungen. Erfolgsaussagen und offene Nachweise stehen im [Phase-1-Prüfbericht](../../../../../docs/testing/PHASE_1_REPORT.md). Der Compose-Testdienst stellt drei getrennte echte Datenbankrollen bereit.

Die paginierte Übersicht lädt aktuelle Versionen gesammelt. Nur der Einzelabruf enthält die vollständige Historie. Der echte PostgreSQL-Test prüft nach einer Änderung sowohl Version 2 in der Liste als auch Versionen 2 und 1 im Detail.
