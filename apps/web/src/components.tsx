import type { ReactNode } from 'react';
import { ApiError, errorText } from './api';
export function ErrorNotice({ error, retry }: { error: unknown; retry?: () => void }) {
  if (!error) return null;
  return (
    <div className="notice error" role="alert">
      <strong>{errorText(error)}</strong>
      {error instanceof ApiError && error.fields !== undefined && (
        <p>
          Bitte alle Pflichtfelder, Zahlenbereiche und Werteformate kontrollieren. Dezimalzahlen
          dürfen ein Komma oder einen Punkt enthalten.
        </p>
      )}
      {error instanceof ApiError && error.requestId && (
        <small>Anfragekennung: {error.requestId}</small>
      )}
      {error instanceof ApiError && error.status === 401 && (
        <a href="/api/v1/auth/login">Erneut anmelden</a>
      )}
      {retry && (
        <button type="button" className="text-button" onClick={retry}>
          Erneut laden
        </button>
      )}
    </div>
  );
}
export function Loading({ text = 'Daten werden geladen …' }: { text?: string }) {
  return (
    <div className="loading" role="status">
      <span className="spinner" />
      {text}
    </div>
  );
}
export function Empty({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="empty">
      <span className="empty-icon" aria-hidden="true">
        ◇
      </span>
      <h3>{title}</h3>
      <div>{children}</div>
    </div>
  );
}
export function Badge({ value }: { value: string }) {
  const labels: Record<string, string> = {
    VERIFIED: 'Geprüft',
    INCOMPLETE: 'Angaben fehlen',
    NO_FEASIBLE_OPTION: 'Keine geeignete Alternative',
    VERIFICATION_FAILED: 'Prüfung fehlgeschlagen',
    ELIGIBLE: 'Zulässig',
    INDETERMINATE: 'Bedingt bewertbar',
    EXCLUDED: 'Ausgeschlossen',
    PASS: 'Erfüllt',
    FAIL: 'Nicht erfüllt',
    UNKNOWN: 'Offen',
    ACTIVE: 'Aktiv',
    REVOKED: 'Gesperrt',
  };
  return <span className={`badge badge-${value.toLowerCase()}`}>{labels[value] ?? value}</span>;
}
export function Field({
  label,
  children,
  hint,
}: {
  label: string;
  children: ReactNode;
  hint?: string;
}) {
  return (
    <label className="field">
      <span>{label}</span>
      {children}
      {hint && <small>{hint}</small>}
    </label>
  );
}
