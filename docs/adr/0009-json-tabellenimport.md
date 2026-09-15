# ADR 0009 — JSON als weiterer M2-Importadapter

Datum: 12.09.2026. Status: implementiert und lokal gezielt geprüft.

JSON wird als weiterer Eingabeadapter an dieselbe deterministische Tabellenpipeline angeschlossen. Die unveränderlichen Originalmetadaten bestimmen das Format anhand der zugelassenen Endung .json oder .jsonl. Es entstehen keine zweite Jobplattform und keine Dateikonvertierung im Browser.

Der erste Umfang unterstützt UTF-8 mit optionalem BOM, ein JSON-Array flacher Objekte beziehungsweise ein Objekt pro JSONL-Zeile. Die erste Objektstruktur bestimmt die Spaltenreihenfolge. Fehlende Schlüssel und null werden in der tabellarischen Ableitung zu leeren Zellen; Originalbytes behalten den Unterschied. Weitere Schlüssel, doppelte Objektschlüssel, verschachtelte Werte, Nichtstandardzahlen, beschädigte Strukturen und zu große Datensätze werden ausdrücklich zurückgewiesen. Zahlen behalten ihre JSON-Schreibweise als Zelltext, boolesche Werte werden true/false. Diese Abbildung wird in der Oberfläche erklärt.

Ein begrenzter Reader liest einzelne Objekte; keine vollständige JSON-Datei im RAM. Bestehende 1-GiB-, Zell-, Datensatz-, Mandanten-, Job- und Bestätigungsgrenzen gelten. Profil, Vorschau, Version, Diagramm und CSV-Export nutzen dieselben Werkzeuge wie CSV. Das Profil trägt source_format zur Herkunft; CSV-Leseoptionen bleiben CSV-spezifisch. Importformate werden nicht durch Agententext gewählt oder freigegeben.

Ein künftiger Data Manager erhält diese typisierten Profile und kann einen geprüften Transformationsplan vorschlagen. Toolrechte, Kosten-/Auftragsgrenzen und die menschliche Versionsbestätigung bleiben serverseitige Grenzen. Es wird keine Live-KI durch den Formatadapter behauptet.

[Prüfbericht](../testing/M2_JSON_REPORT.md). XLSX, Parquet, Datenbankquellen sowie allgemeine verschachtelte JSON-Normalisierung bleiben eigene M2-Schritte.
