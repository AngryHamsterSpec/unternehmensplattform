# Enterprise-Design — lokale Prüfung

Stand: 13.09.2026. Reiner Frontend-/Bedienungsschritt innerhalb von M2; der fachliche Gesamtumfang bleibt TEILWEISE IMPLEMENTIERT.

## Ergebnis

Die vorhandene React-Oberfläche besitzt eine gemeinsame mineralische/graphitgrüne Gestaltung mit gezieltem Messingakzent, gruppierter Navigation, präziser Tabellenhierarchie und konsistentem ECharts-Theme. Tatsächliche Bestandskennzahlen, kombinierte Filter, aufklappbarer Import ohne Entwurfsverlust und fokussierbare Abschnittsaktionen verbessern den Datenworkflow. Native Elemente, lokale Schriften und alle Serververträge bleiben erhalten; keine neue Abhängigkeit.

## Ausgeführte Prüfungen

| Prüfung | Ergebnis |
| --- | --- |
| Finaler Docker-Testbuild: TypeScript, Vite, Prettier, ESLint | bestanden |
| Frontend-Komponententests | 16 bestanden, finaler Lauf 8,89 s |
| OIDC, Profilversionen, Bewertung, Vergleich, Mandantenschutz | bestanden, 7,2 s |
| Lesekonto ohne Schreib-/Administrationsaktionen | bestanden, 1,4 s |
| XSS, Sicherheitsheader, Tastatur, mobile Navigation/390px | bestanden, 2,3 s |
| CSV, Visualisierung, Vorschau, Bestätigung, Export, Rollen | bestanden, 12,3 s |
| CSV-Formaterkennung/Wiederaufnahme, JSON, XLSX mit Vorschau/Version/Export | gezielter Abschluss in Testmandant B bestanden, 15,6 s |
| Parquet mit Bereinigungsnavigation, Vorschau, Version, Original-/Exportvergleich | gezielter Abschluss in Testmandant B bestanden, 5,4 s |
| Browser-Sichtprüfung | Desktop und 390px; lokale IBM Plex Sans geladen; kein horizontaler Seitenüberlauf |

Die ersten vier Browserfälle liefen auf dem ersten überarbeiteten Stand; nach den letzten Layout-/Kontrast- und Scrollkorrekturen wurde der finale Testbuild ausgeführt und die beiden Formatfälle gezielt abgeschlossen. Es wird kein einzelner unveränderter Gesamtlauf mit sechs bestandenen Fällen behauptet. Die Syntaxkorrektur in den neuen Unitfällen wurde vor dem erfolgreichen Testbuild vorgenommen.

Geprüfte Kontrastpaare aus den semantischen Tokens: Sekundärtext auf Arbeitsfläche 5,08:1, primäre Aktion/Weiß 6,76:1, Eingaberand/Weiß 3,20:1 und Navigationstext dunkel 7,30:1. Das ist eine begrenzte Prüfung der zentralen Rollen, keine vollständige WCAG-Zertifizierung.

## Gefundene Umgebungsgrenze

Während der Designprüfung hatte der gemeinsame Mandant Musterwerk IT die damalige feste Grenze von 100 Datensätzen erreicht. Im ersten Browserlauf wurden deshalb die folgenden Excel-/Parquet-Uploads mit HTTP 409 abgelehnt. Die beiden Formatfälle wurden im vorhandenen synthetischen Testmandanten B abgeschlossen, ohne Originaldaten zu löschen oder Backendberechtigungen zu ändern. **Anschließend hat der Nutzer die Quote bewusst zentral konfigurierbar gemacht, Default 1000, mit `check_dataset_quota(db)`.** Die frühere Grenze ist kein offener Fehler und wird nicht wiederhergestellt. Eine langfristige E2E-Isolation bleibt sinnvoll.

## Umfang und Grenzen

Lokales Webimage: `sha256:107d32f2f0c93a20fba8c67f6f6b477f6d3dfddfec36d45877bd32a7e069ed06`. API, PostgreSQL und Web gesund; Datenworker und IdP laufen. API-/Workerstand wurde nicht ausgetauscht.

Keine neuen Backend-, Last-, Restore-, externen KI- oder vollständigen Paket-/Imagescans: Dieser Schritt ändert keine Backenddateien und keine Abhängigkeiten. Sicherheitsprüfungen umfassen die bestehenden realen Rollen-/Mandanten-, CSRF-, XSS- und Headerabläufe. Der bestehende Hinweis auf das separat geladene größere ECharts-Bundle bleibt bestehen. Keine Veröffentlichung oder produktive Abnahme.

[Designreview](../PRODUCT_DESIGN_REVIEW.md) · [Gestaltungsvertrag](../DESIGN_SYSTEM.md) · [Roadmap](../ROADMAP.md).
