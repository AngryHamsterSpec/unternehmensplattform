# ADR 0004 — Gepflegte API-Basis und vollständiger Restore-Ablauf

Datum: 11.09.2026. Status: umgesetzt; aktuelle Prüfnachweise im [Phase-1-Bericht](../testing/PHASE_1_REPORT.md). Ergänzt [ADR 0003](0003-phase1-security-and-performance.md).

## Anlass und Vergleich

Nach der ersten Härtung verblieben 60 hohe/kritische Meldungen im Debian-Bookworm-basierten API-Image. Ein separat gebauter Kandidat auf Python 3.14.7/slim-trixie reduzierte sie auf 54. Ein zweiter Kandidat auf der offiziellen Alpine-Variante installierte dieselben hashgesperrten Python-Abhängigkeiten und ergab im Trivy-Scan keine Paket-Schwachstellen und keine Geheimnisse.

Die Basis wird deshalb auf python:3.14.7-alpine mit geprüftem Digest sha256:c6ead215bfd31f1e433d968853b7a769989117115b728874824e6c0a27cb96fc umgestellt. Ergänzt werden exakt libuuid 2.42.3-r1 und libcrypto3/libssl3 3.5.8-r0. Python-Version, Python-Lockfiles, Benutzer-ID 10001, getrennte Test-/Laufzeitstufen, schreibgeschützter Betrieb und entfernte Paketinstaller bleiben erhalten.

Quelle: [offizielle Python-Imagebeschreibung](https://hub.docker.com/_/python) und [versionierter Alpine-Dockerfile](https://github.com/docker-library/python/blob/688a0b86bb44289df16a363e9f41d90514c1a5f9/3.14/alpine3.24/Dockerfile). Die Digests beider Kandidaten wurden direkt beim offiziellen Registry-Namensraum geprüft.

## Abwägung und Nachweise

Alpine verwendet musl statt glibc. Ein Paketupdate oder spätere native Analysebibliotheken benötigen deshalb erneut einen Installations- und Funktionstest; der erfolgreiche M1-Lauf verspricht keine pauschale Kompatibilität aller künftigen Data-Science-Abhängigkeiten. Es werden keine fremden libc-Pakete oder ungesperrten Compiler-Builds zur Umgehung fehlender Wheels hinzugefügt.

Der Wechsel erfordert vollständige Backendtests gegen PostgreSQL, Typprüfung unter der neuen Laufzeit, echten OIDC-/Browserablauf, neue HTTP-Messung und einen erneuten Scan des endgültigen Images. Der unveränderte Keycloak-Befund und die zwei befristeten Einordnungen aus ADR 0003 bleiben gesondert bestehen.

## Vollständige Wiederherstellungsprüfung

scripts/check_restore.py --full-stack ergänzt den vorhandenen Datenbank-Restore um einen realen separat gestarteten API-/Proxy-/IdP-Stack. Die Originaldatenbank bleibt erhalten. Nur der ursprüngliche Webproxy wird für den Browsertest kurz angehalten, damit der gespeicherte OIDC-Ursprung und die wiederhergestellten Client-Weiterleitungen unverändert funktionieren.

Der restaurierte Stack startet ohne Migration oder erneutes Demo-Seeding. Vier Browserfälle prüfen echten Login, Fachabläufe, Mandantentrennung, Leserechte, XSS-/Header-/Tastaturgrenzen und insbesondere eine bereits vor dem Backup gespeicherte Bewertung mit identischem Ergebnishash. Erst danach wird das App-Passwort ausschließlich in der Restore-Testinstanz rotiert.

Eine finally-Bereinigung entfernt ausschließlich das eigens erzeugte Testprojekt. Der Originalproxy wird auch dann wieder gestartet, wenn diese Bereinigung fehlschlägt. Drei Unitprüfungen sichern diese Fehlerbehandlung ab. Ein positiver Restore-Bericht wird erst nach erfolgreicher Bereinigung und Wiederaufnahme der Demo geschrieben.

Die Prüfung ist ausschließlich für die synthetische lokale Umgebung auf http://localhost:8080 freigegeben. Während der Übung sollen dort keine parallelen fachlichen Änderungen stattfinden; eine Abweichung der Snapshot-Prüfsummen bricht den Test sichtbar ab. Die Option --isolated-browser verwendet unter Windows die gesperrten Browserabhängigkeiten in einem temporären Verzeichnis. Die CI ruft die vollständige Variante auf.
