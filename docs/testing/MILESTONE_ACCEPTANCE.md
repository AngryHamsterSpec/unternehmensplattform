# Abnahmekriterien je Meilenstein

Stand: **9. September 2026**. Diese Kriterien sind verbindliche **Sollzustände**. In Phase 0 sind weder Anwendungscode noch laufende Tests als fertig ausgewiesen. Die tatsächliche Fortschreibung erfolgt in [STATUS.md](../STATUS.md).

## Gemeinsame Abnahmeregel

Ein Meilenstein ist erst abgenommen, wenn sein durchgängiger Fachablauf mit realer Persistenz, Validierung, Autorisierung, API, UI, Fehlerbehandlung, Diagnose und verständlicher Dokumentation funktioniert. Relevante Tests müssen mit Ergebnisbelegen vorliegen. Fehlende Zugangsdaten oder nicht vorhandene Plattformen werden als offene Nachweise dokumentiert.

Jeder Abnahmebericht enthält: Commit/Version, Prüfdatum, verwendete Umgebung, Eingaben, ausgeführte Kommandos, erwartetes und beobachtetes Verhalten, Testergebnisse, verbleibende Grenzen und die Ergebnisse der sechs Reviewperspektiven. Vorlagen, synthetische Preise und simulierte Anbieter werden entsprechend benannt. Eine Produktbehauptung darf nie weiter reichen als der belegte Ablauf.

## M0 – Architektur und umsetzbarer Plan

**Lieferumfang:** Architektur, Implementierungsplan, Roadmap, ADR, Threat Model, vorgeschlagene Repositorystruktur, Domänen-/Datenbankmodell, Agentenhierarchie, Dockerarchitektur, Teststrategie, diese Abnahmekriterien und Technologiematrix, alles auf Deutsch.

Abnahme ist möglich, wenn:

- Die Anforderungen aller Module A bis J einem späteren Meilenstein zugeordnet sind, einschließlich Support, Agent Factory und kontextueller Hilfe.
- Der erste Slice eindeutig eingegrenzt ist und einen tatsächlichen Workflow ergibt.
- Vertrauensgrenzen, Rollen, Mandantenkontext, RLS, Sitzungen und externe Wirkungen explizit beschrieben sind.
- Regeln, Preise, Unsicherheit, Ergebnisse und Versionierung deterministischer Entscheidungen klar getrennt sind.
- Aufwände/Meilensteine als Planung erkennbar sind; keine erfundenen Firmenfakten, IHK-Stunden oder Testresultate vorkommen.
- Technische Annahmen, begründete Vereinfachungen, Alternativen und noch nicht geprüfte Kompatibilitäten sichtbar sind.
- Eine gemeinsame Dokumentationsprüfung widersprüchliche Begriffe, Phasenzuordnungen und gebrochene interne Links beseitigt hat.

**Grenze:** M0-Abnahme ist eine Entwurfsfreigabe. Sie beweist keinen funktionierenden Dockerstack und keine Anwendungssicherheit. Die Reihenfolge bleibt Master-Mandat → Phase 0 → Review → Phase-1-Umsetzung.

## M1 – Erster vollständig nutzbarer Entscheidungsslice

**Module:** A, begrenzter Kern von B und G, gemeinsame Authentifizierungs-/Auditgrundlage.

**Ablauf:** Anmeldung → Organisation/Szenario erfassen → validieren/speichern → deterministisch rechnen → Manager/Cost Estimator/Verifier → Alternativen und Kosten-/Leistungsvergleich → gespeichertes Ergebnis erneut aufrufen.

| Abnahmebereich | Nachweis |
| --- | --- |
| Frischer Start | Dokumentierte Konfiguration und Compose-Start mit leerem Anwendungsvolume; keine externen KI-/Cloud-Zugangsdaten erforderlich. |
| Identität | Echter lokaler OIDC-Login hinter dem Proxy, serverseitige Sitzung, Logout/Widerruf, CSRF und gesicherte Cookie-Konfiguration. |
| Rollen | Organisationsverwaltung, Analyst und Viewer besitzen ausschließlich vorgesehene Rechte; Rollen sind serverseitig geprüft. |
| Mandantentrennung | Zwei Mandanten werden bei Einzelzugriffen, Listen, Vergleich, verschachtelten IDs und direkter SQL-Integration getrennt; negative RLS-/Pooltests bestanden. |
| Intake | Typisierte vollständige P1-Pflichtfelder, eindeutige Einheiten, verständliche Validierung, mehrere Szenarien und Versionskonflikte; maximal zehn Workloads und 20 vollständige Kandidatenpläne je Bewertung. |
| Fachrechnung | Harte Ausschlüsse, normierte Gewichtung, Wirtschafts-/Leistungsmodus, stabile Gleichstände, belegte Annahmen und reproduzierbarer Regelstand. |
| Kosten | Dezimalrechnung, CAPEX/OPEX/TCO-Zeitraum, Währung, Katalog-/Eingabeversion und Herkunft. Fehlende Preise werden nicht erfunden. Synthetische Demoannahmen sind sichtbar. |
| Agentenrollen | Deterministischer Manager orchestriert, Cost Estimator berechnet, Verifier kontrolliert unabhängig. Ausgabe enthält Fakten, Berechnungen, Annahmen und Unsicherheit mit Bezügen. |
| Oberfläche | Deutsche Formulare und Vergleichstabelle; verständliche Leer-/Fehlerzustände, Tastaturbedienung, lesbare Zahlen und Gründe ausgeschlossener Alternativen. |
| Persistenz/Audit | Bewerteter Snapshot, Regel-/Preisversion, Ergebnis und Lauf-/Auditbezug überstehen Reload und Containerneustart; kein verstecktes Chain-of-Thought gespeichert. |
| Ausfälle | DB-/IdP-/API-Timeouts, gescheiterte Migration, Konflikt, verlorene Antwort und Wiederholung führen nicht zu falschem Erfolg oder doppelter Bewertung. |
| Betrieb | Geprüfte Readiness, Loopback-Bindings, keine Produktionsschlüssel im Image, Restore auf frischem Volume und nachvollziehbare Logs. |
| Tests/CI | Statische Prüfungen, Domäne, reale PostgreSQL-/OIDC-Integration, Frontend, Browserworkflow und relevante Security-Gates mit Protokollen. |
| Dokumentation | Quick Start, Module README/EXPLAIN/TESTING, Konfiguration, Docker, Änderungen und ehrliche Funktionsstatus. |

Für P1 sind **SEC-01 bis SEC-12 und SEC-20 bis SEC-22** aus dem [Threat Model](../security/THREAT_MODEL.md) Pflicht. Die funktionierenden CPU-/Hostkombinationen werden einzeln angegeben. `linux/amd64` und `linux/arm64` bleiben Zielplattformen; eine nicht ausgeführte ARM-Prüfung darf nicht als Unterstützung behauptet werden und bleibt ein offenes Portabilitätsgate.

**Optionale Ergänzung:** Eine nachgelagerte KI-Erklärung darf den deterministischen Slice nicht blockieren. Bei Aufnahme muss sie Schema-/Evidenzprüfung, zehn Sekunden Gesamtzeitlimit, keine automatischen Retries, keine Tools und sicheren Ausfall bieten. Ohne Live-Test lautet ihr Status ausdrücklich „nicht live getestet“. Ein optionales LLM ist keine Voraussetzung für die deterministische M1-Abnahme.

**Ausdrücklich später:** Uploads, dauerhafte Jobqueue, Cloudverbindung, Scanner, RAG, Agent Factory und universeller KI-Assistent. Diese Funktionen werden im UI nicht als funktionierend dargestellt.

## M2 – Data Intelligence

**Module:** C sowie benötigte Worker-/Speicherteile von G.

**Ablauf:** Datensatz hochladen → Schema/Qualität prüfen → manuellen oder KI-vorgeschlagenen Transformationsplan ansehen → Vorschau → bewusste Anwendung → neue Version → Visualisierung → Export.

Die Abnahme verlangt unveränderte Originaldateien, Prüfsummen, begrenzte Uploads, lineare Herkunft aller Versionen, typisierte reproduzierbare Transformationen, Vorschauwerte und einen tatsächlich abrufbaren Export. Mehrdeutige Typen und fehlende Werte werden sichtbar. Workerzustände, Lease, Cancellation, Wiederaufnahme und idempotente Ergebnisübernahme sind geprüft. Kein großer Datensatz blockiert den Webprozess.

Negative Dateifälle, Mandantenübergriffe über Objektpfade/Downloads und Prozessabbruch zwischen Datei- und DB-Schritt müssen sicher abgefangen werden. Backup/Restore umfasst jetzt Dateien und DB-Referenzen. Unterstützte Formate werden konkret benannt; CSV zuerst ist zulässig, JSON/XLSX/Parquet und Datenbankquellen bleiben bis ihrem jeweiligen Nachweis offen. Eine Modul-Komplettbehauptung verlangt den vereinbarten Formatumfang. KI-Vorschläge verändern Originale nicht automatisch.

## M3 – Prozessanalyse und Optimierung

**Module:** D, mit explizitem Datenvertrag zu C.

**Ablauf:** Ereignisdaten übernehmen → Daten-/Zeitsemantik prüfen → KPIs berechnen → Engpass belegen → Verbesserung vorschlagen → Ist/Soll vergleichen.

Zyklus-/Wartezeiten, Durchsatz, Nacharbeit und weitere unterstützte KPIs müssen auf überprüfbaren Events beruhen. Fehlende, doppelte, ungeordnete und zeitzonenübergreifende Events erhalten definierte Behandlung. Diagramm und Tabelle stimmen mit den Messungen überein. Verbesserungsaussagen unterscheiden gemessenen Ist-Wert und hypothetischen Nutzen; notwendige Nachmessung wird genannt. Mindestens ein synthetischer Fertigungs-/Betriebsfall läuft vollständig. Keine Empfehlung darf einen kausalen Effekt allein aus Korrelation behaupten.

## M4 – Cloud, FinOps und Resilienz

**Module:** E, zugehörige Rollen und Governance.

**Ablauf:** Autorisierte, zunächst lesende Verbindung bzw. klar markiertes Importszenario → Inventar → Kosten-/Resilienzanalyse → RTO/RPO-/Backup-/RBAC-Vorschlag → nachvollziehbarer Bericht.

Mindestens ein Anbieteradapter muss mit begrenzten Rechten implementiert sein. Ohne Zugangsdaten sind dessen Vertragstests erlaubt, aber keine Live-Behauptung. Preise, Zeiträume, Regions-/Währungsannahmen und unvollständige Inventare werden offengelegt. 403/429/Timeout und Teilantworten sind geprüft. Empfehlungen sind von jeder tatsächlichen Infrastrukturänderung getrennt.

M4 enthält kein Apply. Eine später gesondert beschlossene Schreibfunktion benötigt Plan, Review, menschliche Freigabe und Ausführung als getrennte persistierte Zustände. Inhaltsbindung, Ablauf/Widerruf, Approval-Replay, Race Conditions und Wiederaufnahme nach externer Wirkung sind dann zwingende Abnahmefälle. Bis zu diesen Nachweisen bleibt Apply deaktiviert.

## M5 – Autorisiertes Security-Lab

**Module:** F.

**Ablauf:** Lokales Ziel und Scope registrieren → Berechtigung prüfen → sicheren Scan ausführen → echte Belege übernehmen → Findings normalisieren → fachlich bewerten → menschlich bestätigen/ablehnen → beheben → erneut scannen → schließen.

Ein einziger durchgängiger belegter Scanablauf ist Mindestumfang. Der Scanner liefert echte Ausgabe; die Interpretation kann keine Befunde hinzufügen, die nicht als Hypothese bzw. unbelegt erkennbar wären. Findings enthalten Asset, Schweregrad, Quelle, Evidenz, Konfidenz, Status, Verantwortlichen und Verifikationsanleitung. CVSS/CWE/OWASP-Zuordnung erfolgt nur mit passender Grundlage.

Separates Compose-Projekt und internes Netz, keine Hostfreigabe verwundbarer Dienste, kein Docker-Socket im Backend, keine beliebigen Shellkommandos. Scope-Verletzung, Redirect/DNS-Wechsel, Timeout, defekte Scannerausgabe und unautorisierter Zugriff werden negativ geprüft. Lab-Artefakte bleiben mandantengebunden. Produktionsdateien können keine Lab-Dienste aktivieren.

## M6 – Support mit freigegebenem Wissen

**Module:** I.

**Ablauf:** Freigegebenes Wissen importieren → Frage stellen → autorisierte Belege finden → begründete Antwort oder Eskalation → Feedback erfassen.

Retrieval beachtet Dokumentfreigabe, Tenant und Benutzerrechte auch bei identischen Begriffen. Antworten nennen tatsächlich verwendete Quellen; fehlende Evidenz führt zu Unsicherheit/Eskalation. Vergiftete Dokumente und indirekte Prompt-Injection verändern keine System-/Werkzeugrechte. Versionsänderung und Entzug einer Dokumentfreigabe wirken auf Suche und Antworten. Externe Nachrichten werden ohne menschlich freigegebenen Workflow nicht versendet. Klassifikation, Antwortvorschlag, Feedback und grundlegende Supportauswertung sind nachvollziehbar gespeichert.

## M7 – Agent Factory und kontextueller Assistent

**Module:** H und J, weiterer kontrollierter Ausbau von G.

**Ablauf Factory:** Agentenwunsch → versionierte Spezifikation → Schema-/Rechteprüfung → Verifier/Risk Review → Evaluation → menschliche Freigabe → aktivierte Version.

Abgelehnte Versionen bleiben auditierbar. Neu erzeugte Agenten erhalten keine zusätzlichen Rechte durch ihren eigenen Text. Aktivierung verlangt exakt die geprüfte Inhalts-/Berechtigungsversion. Replay, Parallelaktivierung, geänderte Tools und widerrufene Freigabe werden getestet. Feedback erzeugt neue geprüfte Änderungsvorschläge; produktive Agenten schreiben ihre Regeln nicht selbst um.

**Ablauf Assistent:** Benutzer öffnet ein Modul → erhält rollen- und seitenbezogene Erklärung mit nächsten zulässigen Schritten → kann den Fachablauf auch manuell nachvollziehen. Der Assistent darf keine Rechte aus sichtbarem Seitentext ableiten, keine verborgenen Daten abrufen und keinen ungefragten Seiteneffekt auslösen. Hilfe wird an versionierte echte Produktdokumentation gebunden.

## M8 – Betriebsreife, Leistung und Gesamtprüfung

**Umfang:** Härtung aller freigegebenen Module, plattformübergreifender Betrieb, vollständige Evaluation und Portfolio-/IHK-Nachweise.

Die sieben Gesamtworkflows des Master-Mandats laufen im vereinbarten Funktionsumfang. Offene Risiken SEC-01 bis SEC-22 sind nach Implementierungsstand geprüft und bewertet. Vollständige Wiederherstellung, Geheimnisrotation, Vorfallablauf, Datenaufbewahrung, Last-/Speichergrenzen, Scannerbefunde und Abhängigkeits-/Imageupdates besitzen Belege.

Ein frischer Rechner kann nach Anleitung bauen, starten, anmelden, Demodaten nutzen, Tests ausführen und einen Modulablauf erklären. Linux amd64 und arm64 sowie der angegebene Docker-Desktop-Weg sind tatsächlich geprüft oder weiter ausdrücklich offen. Die Produktionsvorlage ist erst nach gesonderter Umgebungsprüfung produktiv einsetzbar; ein grüner lokaler Test ersetzt keine reale Produktionsfreigabe.

Die IHK-Unterlagen unterscheiden Plattformvision, gewählten kleinen Projektumfang, Eigenleistung, Unterstützung, Planung und tatsächlich erbrachte Ergebnisse. Es werden weder betriebliche Auftraggeber noch Arbeitszeiten, Kosten, Zertifizierungen oder Abnahmen erfunden.

## Statuswerte und Freigabeentscheidung

In Projektberichten gelten die deutschen Statuswerte aus [STATUS.md](../STATUS.md): **IMPLEMENTIERT**, **TEILWEISE IMPLEMENTIERT**, **EXPERIMENTELL**, **NICHT IMPLEMENTIERT**, **BENÖTIGT EXTERNE ZUGANGSDATEN** und **NICHT LIVE GETESTET**. Sie entsprechen den sechs Statusbegriffen im englischen Originalmandat. Ein einzelnes Feature kann implementiert und zugleich nicht live getestet sein; dies muss gemeinsam sichtbar bleiben.

Ein abgebrochener oder übersprungener Test ist kein Erfolg. Ein offenes Gate wird nicht durch das Ende eines Arbeitstages geschlossen. Nach dem M0-Review ist Phase 1 ausschließlich der in diesem Dokument definierte Entscheidungsslice; weitere Meilensteine beginnen auf seiner geprüften Grundlage.

## Tatsächlicher erster CSV-Umfang am 11.09.2026

Die oben beschriebenen M2-Gesamtkriterien bleiben bestehen. Der erste CSV-Ablauf ist gemäß [konkretem M2-Auftrag](../prompts/PHASE_2_IMPLEMENTATION_PROMPT.md) umgesetzt und geprüft. Für diesen begrenzten Worker ersetzen atomare PostgreSQL-Transaktionen eine sichtbare RUNNING-Lease; [ADR 0005](../adr/0005-bounded-csv-data-workflow.md) begründet dies. Cancellation/Dead-Letter-Verwaltung, weitere Formate, umfassende Statistik und KI-Vorschläge bleiben offene Ausbauschritte. Deshalb wird keine vollständige M2-Abnahme behauptet.


## Erweiterung am 12.09.2026

Der Nutzerauftrag zur 1-GiB-Dateigröße aktiviert den nächsten M2-Umfang. Abschnittsspeicher, RUNNING-Leases, Fortschritt, Cancellation und Streaming-Downloads ersetzen für neue Dateien die frühere kleine Gesamttransaktion. Alte Versionen behalten ihren unveränderten Nachweis. Die vollständige 1-GiB-Prüfung ist bestanden; [aktueller Bericht](M2_LARGE_CSV_REPORT.md). Weitere Formate, umfassende Statistik, administrative Dead-Letter-Verwaltung und KI-Vorschläge bleiben für die volle M2-Abnahme offen.


## M2-Abschluss am 14.09.2026

Der [verbindliche M2-Funktionsumfang](../prompts/M2_COMPLETION_SCOPE.md) ist implementiert, integriert und lokal geprüft: Dateien und registrierte PostgreSQL-Quellen, Regeln/Vollanalyse, Berichte, manuelle/geprüfte assistierte Vorschau, ausdrückliche Versionsfreigabe, RLS und Workerzustände. Der letzte Restore-Lauf brach vor dem Backup beim Prüfsummenvergleich von `data_chunks` nach 180 Sekunden ab. **Das aktuelle Restore-Gate bleibt offen.** Auf ausdrückliche jüngste Nutzerentscheidung wird M2 dennoch als erledigt geführt und die Arbeit beendet; dies ist keine vollständige technische Restore-Abnahme. [Abschlussbericht](M2_COMPLETION_REPORT.md). Der optionale externe KI-Adapter bleibt ohne Anbieterzugang NICHT LIVE GETESTET. Keine zusätzliche Testserie und kein Beginn von M3.
