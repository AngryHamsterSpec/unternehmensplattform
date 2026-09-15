# M2 — CSV-Dateien bis 1 GiB

Stand: 12.09.2026. Erweiterung durch ausdrücklichen Nutzerauftrag. Prüfung in Arbeit; noch keine pauschale Freigabe.

## Bereits ausgeführt

- 189 Backendtests mit echter PostgreSQL-Persistenz bestanden, 69,72 Sekunden, keine übersprungenen DB-Prüfungen. Enthalten: neue Stream-Engine und Mehrabschnitt-Upload mit 400.000 Zeilen.
- Strenge mypy-Prüfung: 44 Quelldateien ohne Fehler.
- 13 neue Stream-Domänenprüfungen lokal bestanden.
- Additive Migration 0003 im bestehenden Datenbestand angewandt.
- TypeScript-/Vite-Build, ESLint und Prettier erfolgreich; 10 Frontendtests einschließlich Wiederaufnahme nach Verbindungsfehler bestanden.
- 13 Betriebsskriptprüfungen mit neun zusätzlichen Unterprüfungen bestanden.

## Browser, Betrieb und Sicherheit

Fünf reguläre Browserabläufe bestanden (etwa 1,1 Minuten), einschließlich 4.500.012 Bytes / 450.000 Zeilen in zwei Uploadabschnitten und Abruf der letzten Seite. Wiederaufnahme nach Transportfehler ist zusätzlich im Frontendtest geprüft.

Runtime-Prüfung bestanden: Bereitschaft bei DB-Ausfall 503, Liveness 200, Wiederanlauf 18,306 Sekunden; Worker 256 MiB, eine CPU, internes Netz, Schreibschutz und temporäre Dateien auf Disk-Volume. Abschließender Scan vom 12.09.2026, 05:28 UTC: keine Geheimnisse und keine unbehandelten behebbaren hohen/kritischen Imagebefunde. Bekannte eng befristete Keycloak-Einordnungen bleiben bestehen.

## Offener Restore-Abschluss

Der Lauf vom 12.09.2026, 05:31 UTC durchlief Dump, Neustart, Wiederherstellung in frischem Volume, identische Datenbanksnapshots und RLS-Prüfung. Die anschließende Browserabnahme war insgesamt NICHT erfolgreich: Der CSV-Fall lief in einen inkonsistenten Kopf-/Versionsstand und ein Zeitlimit. Außerdem erwartete das Prüfsystem noch fünf statt sechs Browserfälle. Originalproxy und Worker wurden automatisch wieder aufgenommen.

Beide Ursachen werden mit der Visualisierungserweiterung korrigiert. Ein vollständiger erneuter Restorelauf nach dieser Korrektur bleibt offen; der historische erfolgreiche M2-Restorebericht wird dadurch nicht ersetzt. Auf Nutzerwunsch werden die langen Betriebsabläufe in diesem Visualisierungsschritt nicht wiederholt.

## Funktionsgrenzen

1 GiB pro Originaldatei, 4 MiB je Uploadabschnitt, 256 Spalten, 16.384 Zeichen je Zelle; keine feste Gesamtzeilen-/Gesamtzellenanzahl. Exakte Häufigkeiten, Duplikate und Dezimalaggregate; Ausreißer im neuen Verfahren nicht berechnet. Lokaler Worker mit begrenztem Speicher; keine verteilte Clusterverarbeitung. Nach hartem Prozessabbruch kann administrative Bereinigung temporärer Reste nötig sein.


## Vollständiger 1-GiB-Nachweis

Messung am 12.09.2026, 05:20 UTC im lokalen Linux-/AMD64-Docker-Stack. scripts/benchmark_large_csv.py erzeugte genau 1.073.741.824 Bytes synthetische CSV mit 262.144 Zeilen und vier Spalten. Reguläre synthetische DB-Session im Testmandanten B; kein Auth-Bypass in der Anwendung. Echter OIDC separat im Browser.

| Messung | Ergebnis |
| --- | --- |
| Upload über Nginx/HTTP | 256 Abschnitte, 45,787 s |
| Abschluss und Gesamtprüfsumme | 19,861 s |
| Hintergrundverarbeitung einschließlich Profil und Export | 313,629 s |
| Gesamtlauf einschließlich vollständiger Downloads | 421,869 s |
| Originaldownload | exakt 1.073.741.824 Bytes, SHA-256 identisch |
| Sicherer Exportdownload | 1.076.101.132 Bytes, SHA-256 identisch zum gespeicherten Export |
| Datenprüfung | 262.144 Zeilen, keine Duplikate, Mittelwert Betrag 1,250000; letzte Seite mit 25 Zeilen |

Original-SHA-256: 7c9a319b4208c976c80f6a03e092ad9d76cc594c92bcf68a09eae063ab0a17bd.
Export-SHA-256: f986d3d0477401dd94ebb3fc29a0a5eb5c4fea7d682e5a83ce2efa03465812b4.

Der Worker hatte eine harte Containergrenze von 256 MiB bei einer CPU. Der gemessene cgroup-Höchstwert einschließlich Dateicache erreichte diese Grenze; 0 OOM-Ereignisse und 0 OOM-Kills. Der Prozess-RSS-Höchstwert betrug 130.224 KiB (etwa 127,2 MiB). Die Messung zeigt begrenzten Speicherverbrauch für diesen Datensatz, keine allgemeine Geschwindigkeitszusage für beliebige CSV-Strukturen.

Der Datensatz blieb unter b177392b-1f12-4e10-b50d-ca517aab4675 in der synthetischen Organisation B gespeichert. [Maschinenlesbare Nachweise](m2-large-csv-evidence.json).
