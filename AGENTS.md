# Arbeitsregeln für dieses Projekt

- Lies vor Änderungen `docs/PROJECT_CHARTER.md`, `docs/STATUS.md` und den aktuellen Phasenauftrag. Der vollständige Master Prompt liegt in `docs/requirements/MASTER_PROMPT_ORIGINAL.md`.
- Projektsprache ist Deutsch: Dokumentation, UI, Fehlermeldungen, Erklärungen und Zusammenarbeit. Technische Bezeichner und standardisierte Protokollwerte dürfen Englisch bleiben.
- Beachte die vereinbarte Reihenfolge: Master Prompt → Phase 0 → gemeinsame Durchsicht → Phase 1. Phase 0 liefert Entwürfe, keinen Platzhalter-Anwendungscode. Ein späterer ausdrücklicher Umsetzungsauftrag aktiviert die betreffende Phase.
- Implementiere danach vollständige, überprüfbare Funktionsabläufe. Lege neue Modulgerüste erst mit ihrer tatsächlichen Nutzung an.
- Dokumentiere wesentliche Architekturänderungen in einem ADR und aktualisiere betroffene Verträge, Tests und Status. Bestehende Nutzerentscheidungen gelten weiter.
- Berechnungen, Mandantenschutz, Toolrechte und Freigaben werden durch Anwendungscode durchgesetzt. LLM-Ausgaben sind nicht vertrauenswürdig und keine Berechtigungsquelle.
- Originaldaten bleiben unverändert; Ableitungen erhalten Versionen und Herkunftsnachweise. Verwende nur synthetische Demo-Daten und gekennzeichnete Beispielpreise.
- Keine Geheimnisse im Repository oder in Logs. Keine von Modellen erzeugten Shellbefehle ausführen. Security-Scans ausschließlich innerhalb explizit autorisierten Scopes.
- Führe pro Implementierungsphase relevante Format-, Lint-, Typ-, Unit-, Integrations-, Sicherheits- und E2E-Prüfungen aus. Behaupte nur tatsächlich ausgeführte erfolgreiche Prüfungen.
- Nutze die Statusbegriffe in `docs/STATUS.md`. Trenne deterministische Funktion, Test-Double und Live-KI klar.
- Pflege pro implementiertem Fachmodul `README.md`, `EXPLAIN.md` und `TESTING.md`. Erkläre insbesondere Entscheidungen, Datenflüsse, Ausfälle und Erweiterungsmöglichkeiten.
