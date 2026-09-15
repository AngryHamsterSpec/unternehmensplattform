# Persistierte Bewertungen und Audit

Die API speichert Eingabesnapshot, Profil-/Katalogbezug, Bewertungsoptionen, Ergebnis, Kostenpositionen und drei Agentenläufe als zusammenhängendes Aggregat. Abruf und Vergleich verwenden ausschließlich gespeicherte Ergebnisse. Der Vergleich akzeptiert eine bis fünf IDs derselben aktiven Organisation.

Berechtigter Request + UUID-Idempotenzschlüssel → kurze Transaktion zum Lesen unveränderlicher Eingaben → Rechnung außerhalb der DB-Transaktion → erneute Schreibrechteprüfung unter Organisationslock → Bewertung, Kandidaten, Kostenzeilen, Läufe und Audit → Commit. Derselbe Schlüssel mit gleichem Inhalt liefert das bestehende Ergebnis, mit anderem Inhalt 409.

Siehe [Erklärung](EXPLAIN.md), [Prüfung](TESTING.md) und den [aktuellen Projektstatus](../../../../../docs/STATUS.md).
