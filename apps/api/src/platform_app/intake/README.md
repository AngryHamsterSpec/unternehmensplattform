# Unternehmensszenarien und Versionen

Ein Szenario enthält ein Unternehmensprofil, bis zu zehn Arbeitslasten, vorhandene Assets und übergreifende Anforderungen. Unbekannte Mengen werden als null gespeichert und bleiben von numerischer Null verschieden. Jede Bearbeitung erzeugt eine unveränderliche Profilversion. Historische Versionen sind über die API und die Szenarioansicht auswählbar.

Deutsches Formular → Pydantic-Validierung → Schreibrechte und Organisationslock → Profilkopf plus Version, Workloads und Assets → Audit → gemeinsamer Commit. expected_current_version verhindert das Überschreiben konkurrierender Änderungen. Der Profilkopf verweist auf die neueste Version; gespeicherte Bewertungen behalten ihre konkrete alte Versions-ID.

Siehe [Erklärung](EXPLAIN.md), [Prüfung](TESTING.md) und den [aktuellen Projektstatus](../../../../../docs/STATUS.md).

Die paginierte Übersicht lädt aktuelle Versionen gesammelt. Nur der Einzelabruf enthält die vollständige Historie. Der echte PostgreSQL-Test prüft nach einer Änderung sowohl Version 2 in der Liste als auch Versionen 2 und 1 im Detail.
