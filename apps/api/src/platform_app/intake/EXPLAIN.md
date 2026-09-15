# Entscheidungen und Datenfluss

Deutsches Formular → Pydantic-Validierung → Schreibrechte und Organisationslock → Profilkopf plus Version, Workloads und Assets → Audit → gemeinsamer Commit. expected_current_version verhindert das Überschreiben konkurrierender Änderungen. Der Profilkopf verweist auf die neueste Version; gespeicherte Bewertungen behalten ihre konkrete alte Versions-ID.

## Ausfälle und Grenzen

Unbekannte Felder, ungültige Einheiten, negative Werte, doppelte Workloadkennungen und zu viele Arbeitslasten führen zu 422. Eine fremde ID bleibt 404. Ein veralteter Revisionsstand führt zu 409. Bei Transaktionsfehlern werden weder Version noch dazugehöriger Auditnachweis teilweise committed.

## Erweiterung

Neue Fachfelder müssen in Schema, Formular, generiertem Vertrag, Versionierung und Regelprüfung gemeinsam ergänzt werden. Vorhandene Assets werden dokumentiert; eine automatische Verrechnung als vermiedene Anschaffungskosten existiert im Demo-Katalog nicht.

Die paginierte Übersicht lädt aktuelle Versionen gesammelt. Nur der Einzelabruf enthält die vollständige Historie. Der echte PostgreSQL-Test prüft nach einer Änderung sowohl Version 2 in der Liste als auch Versionen 2 und 1 im Detail.
