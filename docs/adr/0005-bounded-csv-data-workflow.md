# ADR 0005 — Begrenzter CSV-Ablauf und transaktionale Verarbeitung

Datum: 11.09.2026. Status: angenommen für den ersten M2-Umfang.

## Entscheidung

Der Nutzer hat den nächsten CSV-Arbeitsschritt beauftragt. Der modulare Monolith erhält ein Datenmodul mit eigener API, deutschen Seiten und einem separaten Worker aus demselben Image. Bestehende Laufzeit- und Paketpins bleiben erhalten.

Die Dateiverarbeitung akzeptiert ausschließlich UTF-8-CSV mit explizitem Trennzeichen. Originalbytes werden als unveränderliches, mandantengebundenes Objekt gespeichert. Der verwendete BlobStore-Port besitzt zunächst einen PostgreSQL-bytea-Adapter. Bei 128 KiB pro Import ist die gemeinsame Transaktion einschließlich Audit und Backup einfacher und belastbarer als eine zusätzliche S3-Installation. S3 ist eine spätere Adapterimplementierung und wird hier nicht als vorhanden behauptet.

Ein gespeicherter Auftrag enthält bestätigten Mandanten, Urheber und typisierte Operationen. Der Worker verarbeitet nur explizit konfigurierte Organisationen, jeweils unter transaktionslokalem RLS-Kontext. Er besitzt ausschließlich die bestehende Anwendungsrolle, keinen Auth-/Migrationszugang, keine Ports und keinen Internetzugang. Ein neuer Mandant benötigt eine bewusste Erweiterung der Worker-Konfiguration. Die lokale Vorgabe enthält ausschließlich die zwei synthetischen Demoorganisationen.

PostgreSQL-Zeilenlocks mit SKIP LOCKED verteilen wartende Aufträge. Verarbeitung und Ergebnis werden innerhalb einer begrenzten Transaktion abgeschlossen. Beim Prozessabbruch wird diese zurückgerollt; der Auftrag bleibt wartend und wird erneut aufgenommen. Es gibt kein irreführend sichtbares RUNNING ohne Lease. Mitgliedschaft und Schreibrechte werden vor Verarbeitung sowie vor Bestätigung erneut geprüft. Persistierte Fehler enthalten keine Zellenwerte.

Vorschauen sind unveränderliche Auftragsergebnisse mit Hash und Pipelineversion. Bestätigung benennt Vorschau-ID, Hash und erwartete aktuelle Datensatzversion. Eine bereits bestätigte Vorschau liefert idempotent dieselbe Version; konkurrierende andere Vorschauen erhalten einen Versionskonflikt. Originale und gespeicherte Versionen haben für die App keinerlei UPDATE-/DELETE-Rechte. Zusammengesetzte Fremdschlüssel binden alle Verweise an denselben Mandanten und Datensatz.

## Grenzen und Konsequenzen

128 KiB Original, 5.000 Datenzeilen, 40 Spalten, 50.000 Zellen, 1.000 Zeichen je Zelle, 100 Zeichen je Spaltenname, höchstens zehn Transformationsschritte; begrenzte Auftrags-/Datensatzanzahl je Organisation. Der Worker erhält 256 MiB und eine CPU. Die Pipeline ist fest programmierte Fachlogik, kein Python-/SQL-/Shell-Interpreter.

Fehlwerte sind leere oder nur aus Leerraum bestehende Zellen. Zahlen werden konservativ mit Dezimalpunkt erkannt; eine deutsche Dezimalkomma-Zelle wird nicht stillschweigend konvertiert. Qualität zeigt messbare Vollständigkeit und Duplikate; dies ist keine allgemeine fachliche Korrektheitsbewertung.

CSV-Exporte schützen Zellen und Überschriften vor Tabellenkalkulationsformeln durch vorangestelltes Apostroph bei gefährlichen Präfixen, einschließlich führendem Leerraum. Der Export nennt die Anzahl geschützter Zellen sowie seinen eigenen Hash. Der gespeicherte Datenstand bleibt unverändert. Originaldownloads werden als Binärdatei mit .txt-Endung angeboten. Die UI zeigt Herkunft, Versionsstand und Exportunterschiede.

Spätere größere Datenquellen benötigen neue Speicher-, Ressourcen- und Laufzeitnachweise. Erweiterte Statistik, Qualitätsregeln, KI-Vorschläge, andere Dateiformate und S3 bleiben offen.

## Primärquellen

- [Python CSV](https://docs.python.org/3/library/csv.html)
- [PostgreSQL SELECT und SKIP LOCKED](https://www.postgresql.org/docs/18/sql-select.html)
- [OWASP CSV Injection](https://owasp.org/www-community/attacks/CSV_Injection)
