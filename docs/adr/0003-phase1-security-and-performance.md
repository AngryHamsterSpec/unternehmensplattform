# ADR 0003 — Imagepflege und begrenzte Datenbankabfragen

Datum: 11.09.2026. Status: umgesetzt im beauftragten Phase-1-Umfang. Ergänzt [ADR 0002](0002-phase1-runtime-and-contracts.md).

## Anlass

Der reale HTTP-Test überschritt zunächst das Leseziel: Einzelabrufe p95 734,933 ms, Listen 1.356,822 ms. Trivy fand 42 behebbare hohe/kritische Komponentenmeldungen in den vier Laufzeitimages. Ein späterer mobiler Browserfall zeigte Überbreite bei langen Szenarionamen.

## Datenbank und Oberfläche

Session und Nutzer werden in einem Join geladen, aktuelle Organisation, Mitgliedschaft und Rollen in einem weiteren. Der Sessionlock bleibt auf die kurze Auth-Transaktion begrenzt. Rollen werden nicht gecacht; Widerrufe wirken auf die nächste Anfrage. Transaktionslokaler Mandant und Querytimeout werden gemeinsam gesetzt. Zehn Poolverbindungen pro Rolle tragen die vorgesehene Parallelität; Pre-Ping und Rollback beim Zurückgeben bleiben aktiv.

Die Szenarioliste lädt die aktuellen Profilversionen gesammelt. Ihr Feld versions enthält nur den aktuellen Verweis; der Einzelabruf enthält weiterhin die gesamte Versionshistorie. Diese Unterscheidung steht im [API-Vertrag](../API_CONTRACTS.md) und ist durch eine echte PostgreSQL-Regression abgesichert. Unveränderliche Rohstände werden nicht geändert. Lange Texte dürfen innerhalb der verfügbaren Breite umbrechen.

Der zweite HTTP-Lauf mit zehn parallelen Sessions und 200 Szenarien erreichte p95 433,852 ms für Einzelabrufe, 338,812 ms für Listen und 807,785 ms für Bewertungen. Es handelt sich um Sessions einer synthetischen Identität, keine zehn realen Personen. Umgebung und Grenzen stehen im [Prüfbericht](../testing/PHASE_1_REPORT.md).

## Laufzeitimages

Fortschreibung: [ADR 0004](0004-api-base-and-complete-restore.md) ersetzt inzwischen die Debian-basierte API-Laufzeit durch die geprüfte offizielle Alpine-Variante. Die folgenden Entscheidungen zur Paketpflege und Keycloak-Einordnung gelten weiter.

Die Basisimages behalten ihre geprüften Digests. API-Build und Tests benutzen gesperrte Paketinstallationen; der separate Laufzeit-Stage entfernt pip und dessen ensurepip-Wheels. Das beseitigt dort nicht benötigte verwundbare Paketinstaller-Abhängigkeiten.

Nginx erhält libuuid 2.42.3-r1. Das abgeleitete PostgreSQL-18.6-Image erhält libuuid 2.42.3-r1, libcrypto3/libssl3 3.5.8-r0 und su-exec 0.3-r0 aus den signierten Alpine-Paketquellen. Ein geprüfter einzelner Entrypoint-Aufruf wechselt von gosu auf su-exec; die alte Go-Binärdatei wird entfernt. UID-Absenkung, Datenbankversion, Initialisierung und Volume-Pfad bleiben erhalten. Buildprüfung, echter Stackstart und Restore müssen diese Anpassung bestätigen.

Die Paketversionen sind bewusst exakt: Wenn ein Repository sie nicht mehr anbietet, schlägt der Build sichtbar fehl. Ein späteres Update verlangt erneute Prüfung.

## Befundbewertung und Grenzen

Rohberichte bleiben vollständig. Zwei präzise Keycloak-Einordnungen gelten nur für das festgelegte Image, die exakte Paketversion und JAR-Datei bis 10.10.2026:

- CVE-2025-59250: Der enthaltene Microsoft-Treiber 13.2.1.jre11 enthält bereits den Herstellerfix. Die Scanner-Normalisierung zu 13.2.1 führt zur Meldung. [Microsoft-Release](https://github.com/microsoft/mssql-jdbc/releases/tag/v13.2.1).
- CVE-2026-75595: Das Netty-Modul ist enthalten. Die beschriebene Umgehung setzt TLS mit SNI-abhängiger mTLS-Prüfung voraus. Für das überprüfte lokale HTTP-Profil wird fehlende Betroffenheit abgeleitet. Die Konfigurationsprüfung verweigert diese Einordnung bei unbekannten Startoptionen, TLS-/Java-Overrides, zusätzlichen Konfigurationsmounts, veröffentlichten Keycloak-Ports oder öffentlichem Ursprung. [Netty-Advisory](https://github.com/netty/netty/security/advisories/GHSA-c4c3-7fpv-j4q5).

Verantwortliche Wartungsrolle: Projektwartung; technische Bewertung durch Codex am 10./11.09.2026. Dies behauptet keine unabhängige menschliche Sicherheitsfreigabe. Neun Policytests prüfen insbesondere abweichende Versionen, Konfigurationen und Fristablauf. Nach Fristablauf blockieren diese Befunde erneut.

Das lokale Gate verlangt keine gefundenen Geheimnisse und keine unbewerteten behebbaren hohen/kritischen Meldungen. Meldungen ohne Anbieterfix werden gesondert gezählt und bleiben offenes Härtungsrisiko. Dieses Gate ist keine Freigabe für Internetzugang, echte Unternehmensdaten oder produktiven TLS-Betrieb.
