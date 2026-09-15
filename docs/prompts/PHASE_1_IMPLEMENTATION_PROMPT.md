# Phase 1 — Deutscher Umsetzungsauftrag

Dieser Auftrag ist durch die ausdrückliche Nutzeranweisung zum Start von Phase 1 aktiviert.

Lies den vollständigen Master Prompt unter docs/requirements/MASTER_PROMPT_ORIGINAL.md, die deutsche Projektverfassung, AGENTS.md, STATUS.md, alle maßgeblichen Phase-0-Verträge und vereinbarte Reviewänderungen.

Implementiere Phase 1 gemäß docs/PHASE_1_SPEC.md vollständig: Anmeldung über OIDC, serverseitige Sessions, RBAC und Mandantentrennung; versionierte Unternehmensszenarien; deterministische Architektur- und Kostenbewertung; Manager, Cost Estimator und unabhängiger Verifier; deutsche Ergebnis- und Vergleichsoberfläche; echte PostgreSQL-Persistenz; Audit; reproduzierbare synthetische Demo; Docker und CI.

Beginne mit Repository-Prüfung und dem Kompatibilitätsnachweis für stabile Versionen, OIDC, Proxy, Migration und PostgreSQL-RLS. Nutze separate Datenbankrollen. Halte den gewählten modularen Monolithen einfach und erkläre Abweichungen per ADR.

Implementiere anschließend den gesamten Ablauf vom Formular bis zum nach Neustart wieder sichtbaren geprüften Ergebnis. Trenne Service-, Deployment- und Hostingmodelle. Harte Constraints gehen vor Gewichtung. Synthetische Preise bleiben sichtbar als Demo gekennzeichnet; fehlende Werte erzeugen keine erfundene Empfehlung.

Integriere den optionalen OpenAI-Erklärungsadapter hinter dem Provider-Port. Das deterministische Kernprodukt funktioniert ohne API-Schlüssel. Live-KI darf nur minimierte freigegebene Daten sehen und erhält in Phase 1 keine Tools. Ein fehlender Live-Test wird ausdrücklich ausgewiesen.

Führe tatsächlich Formatierung, Lint, Typprüfung, Unit-, PostgreSQL-, API-, Berechtigungs-, Tenant-, Providervertrags-, Browser-E2E- und relevante Sicherheitsprüfungen aus. Prüfe Idempotenz, Versionskonflikte, Rollbacks, KI-Ausfall, Neustart und Restore. Verwende keine Test-Doubles anstelle echter Persistenz oder Anmeldung im Abnahmeablauf. Korrigiere entdeckte Probleme.

Erstelle README.md, EXPLAIN.md und TESTING.md für implementierte Module. Aktualisiere Architektur, Nachweise, STATUS.md und CHANGELOG.md. Berichte zum Abschluss konkrete nutzbare Funktionen, ausgeführte Prüfungen und verbleibende Einschränkungen.

Stoppe nicht nach Gerüst, Design oder einem unvollständigen Dashboard. Liefere den definierten M1-Ablauf durchgängig; beginne spätere Fachmodule erst nach seiner Abnahme.
