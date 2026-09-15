# Prüfung

test_explanations.py verwendet ausdrücklich AsyncMock am Provider-Port: Datenminimierung, Evidenzbindung, Limits, Verweigerung, kein Retry/Tool/Storage. test_explanation_state.py prüft veraltete Reservierungen. Die DB-Integration prüft parallele identische Requests, genau eine Reservierung, Ausfall, Budgetgrenze und unveränderte Bewertungs-Hashes. Das ist kein echter OpenAI-API-Aufruf.

Aus dem Repositoryroot:

```sh
python -m pytest apps/api/tests -p no:cacheprovider -q
docker compose --profile test run --build --rm tests
```

DB-Prüfungen werden ohne RUN_DB_TESTS=1 ausdrücklich übersprungen. Erfolgsaussagen und offene Nachweise stehen im [Phase-1-Prüfbericht](../../../../../docs/testing/PHASE_1_REPORT.md). Der Compose-Testdienst stellt drei getrennte echte Datenbankrollen bereit.
