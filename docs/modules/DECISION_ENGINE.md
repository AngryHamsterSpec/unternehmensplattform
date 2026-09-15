# Entscheidungslogik für Architektur und Kosten

Status: ENTWURF, M1. Die folgenden Regeln sind ein spezifizierter Rechenkern, keine bereits implementierte oder empirisch validierte Beratung.

## Welche Entscheidung wird unterstützt?

Ein Unternehmen kann unterschiedliche Arbeitslasten verschieden betreiben. Ein öffentlich gehostetes SaaS-Produkt und eine lokale Fachanwendung können zusammen einen verbundenen Gesamtplan bilden. Die Engine vergleicht daher vollständige, begrenzte Pläne pro Szenario.

Die drei Achsen sind service_model (SAAS, PAAS, IAAS, SELF_MANAGED), deployment_model (PUBLIC_CLOUD, PRIVATE_CLOUD, TRADITIONAL) und hosting_location (PROVIDER, ON_PREMISES, COLOCATION). „Hybrid“ ist eine Eigenschaft eines integrierten Gesamtplans. Eine versionierte Kompatibilitätsmatrix verhindert unsinnige Kombinationen; klassische lokale Server werden nicht automatisch als Private Cloud bezeichnet.

M1 unterstützt höchstens 10 Arbeitslasten und 20 vollständig beschriebene Pläne. Die UI zeigt „20 unterstützte Pläne geprüft“, keine Behauptung einer global optimalen Architektur.

## Eingaben und Evidenz

Ein ScenarioSnapshot enthält Unternehmensprofil, Arbeitslasten, Lastannahmen, Standorte, Personal/Kompetenzen, Budget, regulatorische Anforderungen als Nutzerangaben, Latenz, RTO/RPO und Verfügbarkeit. Numerische Werte erhalten Einheit und Wertebereich. „Unbekannt“ ist zulässig und bleibt von Null verschieden.

CandidateSpec enthält Fähigkeiten, Kapazitäts-/RTO-/RPO-Nachweise, Abhängigkeiten, Integrationsaufwand, Preiskatalogreferenzen und Einschränkungen. Ein Kandidat gilt nur innerhalb seiner belegten Betriebs- und Lastannahmen. Jeder abgeleitete Wert referenziert Eingabe-, Regel- oder Katalogevidenz.

## Algorithmus

1. Validierung: endliche Zahlen, positive Horizonte und Skalengrenzen, nichtnegative Mengen/Preise/Gewichte, Budgetwährung, unterstützte Kombinationen. NaN, Infinity, negative Gewichte und Summe null sind Fehler.
2. Kandidatenbildung aus dem begrenzten versionierten Katalog; die Engine generiert keine unbelegte Cloud-Konfiguration.
3. Harte Constraints prüfen: Muss-Region, erforderliche Funktion, maximale Latenz, Personalvoraussetzungen, RTO/RPO, Verfügbarkeit, optional hartes Budget.
4. Je Muss-Bedingung PASS, FAIL oder UNKNOWN. FAIL schließt einen Plan aus. UNKNOWN lässt ihn nur als „bedingt bewertbar“ erscheinen; kein bestätigter Gewinner, solange erforderliche Evidenz fehlt.
5. Kosten und Nutzen der verbleibenden vollständigen Pläne berechnen. Fehlende relevante Kosten blockieren einen belastbaren TCO-/Budgetvergleich.
6. Bewertung je Dimension mittels versionierter, ausdrücklich begründeter Skala. 0 bedeutet schlechteste und 100 beste Zielerfüllung. Grenzwerte hängen an fachlichen Ankern, nicht an der zufälligen Kandidatenauswahl.
7. score(a) = Summe(w_i × s_ai) / Summe(w_i). Score liegt zwischen 0 und 100, wenn alle s_ai im erlaubten Bereich liegen.
8. Verifier prüft Einzelwerte, Summen, Constraints, Evidenzreferenzen und Ergebnisreihenfolge. Bei Inkonsistenz keine freigegebene Empfehlung.
9. Vergleiche ausgeben: zulässige Alternativen, Ausschlüsse samt Grund, Einzelbeiträge, Annahmen, Risiken und notwendige Klärungen.
10. Sensitivität zeigen: Gewicht jeder Dimension einzeln relativ um ±20 % ändern und wieder normalisieren. Anzahl geänderter Sieger und Scoreabstand dokumentieren; keine statistische Wahrscheinlichkeit daraus machen.

Fehlt ein gewichtetes Kriterium, wird es nicht stillschweigend entfernt und das Gewicht nicht auf andere Dimensionen verteilt. Das Ergebnis bleibt unvollständig. Bei vollständigem Datensatz können alle Kriterien geprüft werden; bei keinem zulässigen Kandidaten lautet das Ergebnis „Keine belegbar geeignete Alternative“.

## Bewertungsdimensionen

Kosten, Leistung, Verfügbarkeit, Betriebskomplexität, Personalbedarf, Sicherheit, Anbieterbindung, Skalierung, Sensitivität, Latenz, Wartung, Backup, Wiederanlauf und Bereitstellungszeit sind im Modell vorgesehen. Um Doppelgewichtung zu vermeiden, dokumentiert jede Regel die Abgrenzung: z. B. RTO als Muss-Grenze und darüber hinausgehender nachgewiesener Wiederanlaufspielraum als Nutzen, nicht zweimal derselbe Punktwert.

M1 muss für jedes tatsächlich aktivierte Kriterium messbare Inputs, Skala und Evidenz liefern. Nicht belegbare Dimensionen werden sichtbar als offen geführt und verhindern einen vollständigen Score, wenn sie positiv gewichtet sind.

## Gewichte und Annahmen

Wirtschaftlichkeit und Leistung sind versionierte Presets, keine allgemeinen Wahrheiten. Die Demo kann folgende verdichtete Gruppen verwenden; die Zuordnung der Detailkriterien ist Bestandteil der Regelversion:

| Gruppe | Wirtschaftlichkeit | Leistung |
| --- | ---: | ---: |
| TCO | 35 | 15 |
| Leistung/Latenz/Skalierung | 15 | 35 |
| Verfügbarkeit/Backup/Wiederanlauf | 20 | 25 |
| Betrieb/Personal/Wartung | 20 | 10 |
| Sicherheit/Sensitivität/Bindung/Bereitstellung | 10 | 15 |

Diese Gewichte sind vorgeschlagene Demo-Konfiguration. Sicherheit-Mussbedingungen gelten unabhängig davon. Nutzerdefinierte Gewichte sind zulässig und werden zusammen mit dem Ergebnis gespeichert.

## Durchgerechnetes synthetisches Beispiel

Zur Formelprüfung dienen nur drei verdichtete Kriterien, ohne Aussage über echte Produkte:

| Kandidat | Kosten-Nutzen | Leistung | Betrieb | Gewicht 0,5 / 0,3 / 0,2 |
| --- | ---: | ---: | ---: | ---: |
| A | 80 | 60 | 90 | 76 |
| B | 60 | 90 | 70 | 71 |

A: 0,5×80 + 0,3×60 + 0,2×90 = 76. B: 30 + 27 + 14 = 71. Diese korrekten Werte bilden die Referenz für den Golden-Test.

Separater Manipulationstest: Wird B bei unveränderten Beiträgen mit 72 angeliefert, muss der Verifier die Tabelle verwerfen. Eine flüssige Erklärung ersetzt keine Rechenprüfung.

## TCO, CAPEX und OPEX

Für einen expliziten Zeitraum H Monate:

M1: TCO = Summe aller einmaligen Kosten + Summe monatlicher Betriebs-, Lizenz-, Personal-, Netzwerk-, Backup- und Supportkosten über H Monate. Jede Kostenzeile ist zusätzlich CAPEX oder OPEX zugeordnet; damit gilt TCO = CAPEX gesamt + OPEX gesamt. Die zeitliche Abrechnung und die Kostenkategorie sind unterschiedliche Felder.

CAPEX und OPEX werden separat ausgewiesen. Abschreibung wird nicht zusätzlich zum Anschaffungspreis in den Cash-TCO addiert. M1 rechnet undiskontiert und ohne Restwert. Spätere Formelversionen können Restwert, gesonderte Ausstiegskosten und eine Kapitalwertbetrachtung mit dokumentiertem Zinssatz ergänzen. Gemeinsame Kosten werden einmal auf Planebene oder über nachvollziehbare Allokation berücksichtigt.

Beispiel, vollständig synthetisch: 12.000 EUR Anschaffung + 3.000 EUR Migration + 36 × 700 EUR Betrieb = 40.200 EUR TCO. Vergleichsplan mit 1.000 EUR Einrichtung + 36 × 1.200 EUR Betrieb = 44.200 EUR. Das Beispiel beweist nur die Rechnung, keine reale Preisüberlegenheit.

Katalogeintrag: Quelle, Version, Preisstand, Gültigkeitsende, Region, SKU/Leistungsumfang, Einheit, Währung, Steuerbasis, Preisstaffel und Kennzeichen SYNTHETIC oder SOURCED. M1 nutzt synthetische EUR-Daten, netto als klar benannte Annahme. Kein versteckter Wechselkurs. Bei fehlendem Preis steht „nicht berechenbar“, nicht 0 EUR. Abgelaufene Preise werden gekennzeichnet und verhindern eine aktuelle verbindliche Kostenbewertung.

## Vertrauenswürdigkeit und Ausgabe

Confidence wird in drei erklärte Angaben zerlegt: Evidenzabdeckung, Vollständigkeit und Rangstabilität. Keine erfundene Angabe „94 % sicher“. Ein Score ist Nutzen unter Annahmen und keine Ausfallwahrscheinlichkeit.

Das Ergebnis trennt facts, evidence, calculations, assumptions, inferences, recommendations, uncertainty und required_human_decision. KI-Erklärungen verweisen auf diese gespeicherten Felder und dürfen kein Ranking überschreiben. Eine menschliche Auswahl kann abweichen, benötigt dann aber eine gesonderte begründete Decision mit unverändertem ursprünglichem Assessment.
