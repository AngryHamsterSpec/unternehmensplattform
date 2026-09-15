# Prüfung

test_database_integration.py prüft reale Persistenz, Idempotenz, Konflikte, RLS, mandantenfremde IDs und atomaren Audit. Die echten Browserprüfungen öffnen Bewertungen nach Reload und vergleichen zwei Modi. scripts/check_restore.py prüft fachliche Hashes nach API-Neustart und in einem gesonderten frischen PostgreSQL-Volume.

Aus dem Repositoryroot:

```sh
python -m pytest apps/api/tests -p no:cacheprovider -q
docker compose --profile test run --build --rm tests
```

DB-Prüfungen werden ohne RUN_DB_TESTS=1 ausdrücklich übersprungen. Erfolgsaussagen und offene Nachweise stehen im [Phase-1-Prüfbericht](../../../../../docs/testing/PHASE_1_REPORT.md). Der Compose-Testdienst stellt drei getrennte echte Datenbankrollen bereit.

Der vollständige Restorelauf mit python scripts/check_restore.py --full-stack prüft zusätzlich echten OIDC-Login am wiederhergestellten IdP und den unveränderten Hash einer historischen Bewertung. Die Wiederaufnahme des Originalproxies wird durch scripts/test_restore_cleanup.py auch für Fehlerfälle geprüft.
