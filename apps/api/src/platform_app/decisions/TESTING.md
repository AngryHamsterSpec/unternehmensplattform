# Prüfung

test_decisions.py, test_decision_regressions.py und test_properties.py prüfen TCO, CAPEX/OPEX, fehlende Werte, Grenzen, Verfälschungen, Gewichte, Rangfolgen und Sensitivität. Hypothesis untersucht zusätzliche generierte Eingaben. scripts/benchmark_decisions.py misst zehn Arbeitslasten und vier Kandidaten samt Verifier, ohne DB oder HTTP.

Aus dem Repositoryroot:

```sh
python -m pytest apps/api/tests -p no:cacheprovider -q
docker compose --profile test run --build --rm tests
```

DB-Prüfungen werden ohne RUN_DB_TESTS=1 ausdrücklich übersprungen. Erfolgsaussagen und offene Nachweise stehen im [Phase-1-Prüfbericht](../../../../../docs/testing/PHASE_1_REPORT.md). Der Compose-Testdienst stellt drei getrennte echte Datenbankrollen bereit.
