# Lernpfad zum Erklären und Weiterentwickeln

Status: geplanter Lernpfad, kein behaupteter Kenntnisnachweis.

## Mit M1 lernen

1. Ein Szenario vom Formular über DTO, Service und Transaktion bis PostgreSQL verfolgen.
2. Eine neue gewichtete Regel ergänzen und ihre Grenzen an einem Golden-Test erklären.
3. Einen Tenant-Zugriff ohne Filter provozieren und die zusätzliche RLS-Schranke nachweisen.
4. Einen Versionskonflikt reproduzieren und erklären, warum eine ältere Bearbeitung keine neue überschreibt.
5. Den synthetischen TCO selbst nachrechnen und Anschaffung von Abschreibung unterscheiden.
6. Provider-Ausfall auslösen und zeigen, weshalb die gespeicherte Fachentscheidung intakt bleibt.
7. Ein Backup in eine leere Datenbank zurückspielen und die Unterschiede zwischen Backup und geprüftem Restore erklären.

## Fragen für ein Fachgespräch

Warum ein modularer Monolith? Warum PostgreSQL? Was schützt RLS und was nicht? Warum kein LLM für TCO? Was bedeuten unbekannte Daten? Wie werden Freigaben an eine konkrete Aktion gebunden? Wie unterscheidet sich ein Idempotency-Key von einer Datenbank-ID? Welche Daten darf ein Sprachmodell sehen?

## Lernnachweise

Pro Meilenstein eine kurze eigene Erklärung, einen selbst nachvollzogenen Testfall und eine kleine begründete Änderung festhalten. Implementierte Module beantworten in EXPLAIN.md: Problem, Architekturgrund, wesentliche Funktionen, Datenfluss, Tabellen, Ausfälle, Erweiterung und Tradeoffs.

M2 ergänzt Datenprofiling/Lineage; M3 Zeitdaten/KPIs; M4 Kostenquellen/Resilienz; M5 Scannerbeleg vs. Interpretation; M6 Berechtigungen im Retrieval; M7 Versionierung/Evaluation. Zu jeder Fähigkeit gehört ein demonstrierbarer Ablauf.
