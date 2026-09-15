# Entscheidungen und Datenfluss

Konfiguration und Organisationsfreigabe + Schreibrolle + ausdrückliche Zustimmung → VERIFIED-Bewertung lesen → Namen/Freitext entfernen → Idempotenz und pessimistische Tagesbudgetreservierung unter DB-Lock → Commit → Responses-Aufruf mit strukturiertem Schema → Referenzen prüfen → getrennten Erklärungssnapshot und Audit speichern. Die Originalbewertung bleibt unverändert.

## Ausfälle und Grenzen

OPENAI_ENABLED benötigt OPENAI_API_KEY, OPENAI_MODEL, OPENAI_PRICE_VERSION, OPENAI_INPUT_PER_MILLION, OPENAI_OUTPUT_PER_MILLION, OPENAI_DAILY_BUDGET und OPENAI_ORGANIZATION_IDS. Preise sind explizit in USD je Million Tokens anzugeben und vor Aktivierung zu prüfen. Höchstens 8.000 konservativ begrenzte Inputtokens, 1.200 Outputtokens, zehn Sekunden Gesamtzeit, null Tools, null automatische Retries und store=false. Providerfehler werden ohne fremde Fehlertexte gespeichert. Reservierungen bleiben bei Fehlern bestehen.

## Erweiterung

Eine offene Reservierung wird nach 30 Sekunden in der Leseansicht INDETERMINATE: Der externe Ausgang ist unbekannt. Ein erneuter gleicher Schlüssel löst keinen zweiten Aufruf aus. GET /explanation-requests/{id} liefert bei laufender Reservierung 202, sonst 200. Eine Freigabe-/Budgetänderung braucht lokale Administration der Konfiguration. Weitere Provider implementieren denselben Port und benötigen eigene Vertrags- und Live-Nachweise.
