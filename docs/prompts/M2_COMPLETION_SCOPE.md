# M2 — verbindlicher Abschlussumfang

Aktiviert durch den ausdrücklichen Nutzerauftrag, M2 vollständig abzuschließen und danach zu stoppen. Aktueller Branch und manuelle Änderungen einschließlich `dataset_limit_per_organization=1000` bleiben erhalten. M3 wird nicht begonnen.

1. Vorhandene CSV-/JSON-/XLSX-/Parquet-/SQLite-Workflows erhalten.
2. Direkte PostgreSQL-Quellen: betreiberseitig registrierte, mandantengebundene Verbindungen mit erlaubten Tabellen; Schemaübersicht, persistenter begrenzter Snapshotauftrag, Originalhash und bestehender Import-/Versionsworkflow. Echte synthetische PostgreSQL-Quelle prüfen.
3. Versionstreue Hintergrundanalysen: Schema/Fehlwerte/Duplikate, genaue statistische Kennzahlen und Verteilungen, IQR-Ausreißer, ungültige Werte, Pearson-Korrelation und zeitliche Aggregation mit expliziten Grenzen. Korrelation ist kein Kausalitätsbeleg.
4. Wiederverwendbare unveränderliche Qualitätsregelsätze; Regeln und Ergebnisse im Analysesnapshot, nachvollziehbarer Qualitätsscore und Export als JSON/lesbarer HTML-Bericht.
5. Assistierte Bereinigung: deterministische Vorschläge klar kennzeichnen; separater echter strukturierter KI-Adapter mit Datenminimierung, expliziter externer Freigabe, Budget und Zeitlimit. Supervisor → Data Manager → Spezialist; unabhängiger Verifier/Risk Reviewer/Cost Estimator/Approval Gate. Pläne erhalten Quellversion, Hash, Regel-/Promptversion und Audit. Keine Ausführung von Modellcode; nur vorhandene typisierte Schritte nach Vorschau und ausdrücklicher Bestätigung.
6. Neue Aufträge besitzen RLS, Rechteprüfung, Lease, Abbruch, sichere Wiederaufnahme und sichtbare Fehlerhistorie. Ein verlorener externer KI-Ausgang wird nicht automatisch kostenpflichtig wiederholt.
7. Integration, kurze gezielte Prüfungen, erforderliche Migration-/Betriebsnachweise und aktualisierte Modul-/Sicherheits-/Abnahmedokumentation. Fehlende externe Live-Nachweise bleiben ausdrücklich benannt.

ML-Clustering, Prognosemodelle, verteilte Rechencluster und zusätzliche Anbieter werden nur bei fachlichem Bedarf ergänzt; normale Statistik ist für den vorhandenen Umfang die gewählte Lösung. Keine ungenutzten ML-Gerüste. Produktiver Betrieb und die Gesamtabnahme M8 bleiben getrennt.
