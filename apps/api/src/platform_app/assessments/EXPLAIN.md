# Entscheidungen und Datenfluss

Berechtigter Request + UUID-Idempotenzschlüssel → kurze Transaktion zum Lesen unveränderlicher Eingaben → Rechnung außerhalb der DB-Transaktion → erneute Schreibrechteprüfung unter Organisationslock → Bewertung, Kandidaten, Kostenzeilen, Läufe und Audit → Commit. Derselbe Schlüssel mit gleichem Inhalt liefert das bestehende Ergebnis, mit anderem Inhalt 409.

## Ausfälle und Grenzen

Verlorene Antworten führen beim Wiederholen nicht zu doppelten Bewertungen. Eine während der Rechnung entzogene Berechtigung verhindert den Commit. Fremde direkte IDs und gemischte Vergleiche werden abgewiesen. Die Anwendungsrolle besitzt keine Update-/Delete-Rechte auf historische Bewertungen oder Auditzeilen.

## Erweiterung

Neue Ausgabefelder gehören in den typisierten Ergebnisvertrag und den Verifier. Andere Preis-/Regelstände erfordern neue Bewertungen. Eine dauerhafte Jobqueue und Exporte beginnen in späteren Phasen; die begrenzte Phase-1-Rechnung bleibt synchron.
