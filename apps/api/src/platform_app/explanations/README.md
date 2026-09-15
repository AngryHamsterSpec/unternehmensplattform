# Optionale KI-Erklärungen

Die deterministische Bewertung funktioniert ohne externen Anbieter. Der optionale OpenAI-Adapter formuliert ausschließlich bereits geprüfte Ergebnisse. Er ist standardmäßig deaktiviert und NICHT LIVE GETESTET. Eine lokale Providerfreigabe ersetzt nicht die Zustimmung zur einzelnen Übertragung.

Konfiguration und Organisationsfreigabe + Schreibrolle + ausdrückliche Zustimmung → VERIFIED-Bewertung lesen → Namen/Freitext entfernen → Idempotenz und pessimistische Tagesbudgetreservierung unter DB-Lock → Commit → Responses-Aufruf mit strukturiertem Schema → Referenzen prüfen → getrennten Erklärungssnapshot und Audit speichern. Die Originalbewertung bleibt unverändert.

Siehe [Erklärung](EXPLAIN.md), [Prüfung](TESTING.md) und den [aktuellen Projektstatus](../../../../../docs/STATUS.md).
