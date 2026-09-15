# ADR 0006 — CSV-Dateien bis 1 GiB

Datum: 12.09.2026. Nutzerauftrag: die bisherige 128-KiB-Demogrenze durch einen Import bis 1 GiB ersetzen.

## Entscheidung

Neue Dateien werden in Abschnitten von höchstens 4 MiB hochgeladen. PostgreSQL speichert unveränderliche Abschnitte hinter mandantengebundenen Speicherobjekten. Uploads reservieren ihre deklarierte Größe; die Anwendung begrenzt aktive Uploads und den Speicher je Organisation. Wiederholte Abschnitte mit gleichem Hash sind idempotent. Abschließen prüft die vollständige SHA-256 durch begrenztes Lesen und veröffentlicht Original, Datensatz und Auftrag atomar. Unvollständige Uploads lassen sich abbrechen.

Der Worker beansprucht einen Auftrag in einer kurzen Transaktion. Lease, Fortschritt, Wiederaufnahme nach Ablauf und Abbruch ersetzen eine minutenlange Organisationstransaktion. Nur der aktuelle Lease-Inhaber mit weiterhin gültiger Schreibberechtigung darf ein Ergebnis veröffentlichen. Temporäre Dateien und SQLite liegen auf einem separaten Docker-Arbeitsvolume; der Heap wächst nicht mit der Dateigröße.

CSV wird zeilenweise verarbeitet. SQLite verwendet einen begrenzten Cache und dateibasierte Sortierung für exakte Häufigkeiten, verschiedene Werte und Duplikate. Profil und Vorschau sind begrenzt; Zeilenzahl und Zellenzahl haben keine alten 5.000-/50.000-Grenzen. Schutzgrenzen bleiben 256 Spalten, 16.384 Zeichen je Zelle und 4 MiB je CSV-Datensatz. Numerische Aggregate verwenden Dezimalarithmetik. Ausreißer werden für große Daten ausdrücklich als nicht berechnet ausgewiesen.

Neue Versionen verwenden indizierte JSONL-Abschnitte; 25-Zeilen-Seiten lesen nur betroffene Abschnitte. Der sichere CSV-Export wird im Worker erzeugt. Downloads streamen die gespeicherten Abschnitte unmittelbar in den Browser-Downloadmanager.

## Bestand und Betrieb

Migration 0003 erweitert das Schema additiv. Bestehende kleine Blobs und Versionen bleiben unverändert lesbar. Der alte JSON-Import bleibt als begrenzter Kompatibilitätsendpunkt bestehen; die Oberfläche verwendet ausschließlich den neuen Upload.

Originale und Ableitungen bleiben in PostgreSQL und damit im bestehenden Datenbank-Backup. Das Arbeitsvolume enthält nur wiederherstellbare temporäre Dateien. Die lokale Grenze von 20 GiB je Organisation und 8 GiB je Ableitung begrenzt den Demo-Betrieb. 1 GiB ist eine Dateigrenze, keine Zusage verteilter Verarbeitung beliebig großer Datenmengen.

## Nachweise

Implementierung und Messungen werden im Status und separaten Prüfbericht dokumentiert. Ein gesetzter Grenzwert allein gilt nicht als Nachweis für einen erfolgreichen 1-GiB-Import.
