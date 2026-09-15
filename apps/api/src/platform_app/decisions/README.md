# Deterministische Architektur- und Kostenbewertung

evaluate bildet den Manager: Es prüft vier Demo-Pläne, lässt den Cost Estimator Dezimalkosten ermitteln und ruft den unabhängigen Verifier auf. Ergebniszustände sind VERIFIED, INCOMPLETE, NO_FEASIBLE_OPTION und VERIFICATION_FAILED. Harte Bedingungen gehen vor der gewichteten Rangfolge.

Typisiertes Szenario + Bewertungsoptionen + unveränderlicher Preiskatalog → Kapazitäts-/Regions-/Personal-/Budget-/Sicherheitsbedingungen → Kostenzeilen und Kriterien → normierte Gewichte und stabile Rangfolge → zehn Sensitivitätsvarianten → unabhängige Nachrechnung. Service-, Deployment- und Hostingmodelle sind getrennte Achsen; Hybrid ist ein Plan mit verbundenen Komponenten.

Siehe [Erklärung](EXPLAIN.md), [Prüfung](TESTING.md) und den [aktuellen Projektstatus](../../../../../docs/STATUS.md).
