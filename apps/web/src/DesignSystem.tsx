import { useState } from 'react';
import type { ReactNode } from 'react';

const paths = {
  compass: 'M12 2v3m0 14v3M2 12h3m14 0h3M16.5 7.5l-3 6-6 3 3-6 6-3Z',
  scenarios: 'M3 3h7v7H3zM14 3h7v7h-7zM3 14h7v7H3zM14 14h7v7h-7z',
  compare: 'M3 7h17m-4-4 4 4-4 4M21 17H4m4-4-4 4 4 4',
  data: 'M3 4h18v16H3zM3 9h18M8 9v11M14 9v11',
  audit: 'M6 3h12v18H6zM9 7h6M9 11h6M9 15h4',
  people:
    'M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8Zm-7 9v-2a7 7 0 0 1 14 0v2M17 4a4 4 0 0 1 0 7m2 3a5 5 0 0 1 3 5',
  density: 'M3 5h18M3 9h18M3 13h18M3 17h18M3 21h18',
  search: 'M10.5 17a6.5 6.5 0 1 0 0-13 6.5 6.5 0 0 0 0 13Zm5-1 5 5',
  bar: 'M4 19V9h3v10m4 0V4h3v15m4 0v-7h3v7M2 21h21',
  donut: 'M12 3v9h9A9 9 0 1 1 12 3Zm3 0a9 9 0 0 1 6 6h-6V3Z',
  line: 'M3 3v18h18M5 16l4-5 4 3 7-9',
  scatter: 'M3 3v18h18M8 15h.1M11 10h.1M16 12h.1M18 6h.1',
  plus: 'M12 5v14M5 12h14',
  upload: 'M12 16V3m-5 5 5-5 5 5M4 15v6h16v-6',
  chevron: 'm9 5 7 7-7 7',
  menu: 'M4 6h16M4 12h16M4 18h16',
  close: 'm6 6 12 12M6 18 18 6',
  file: 'M14 2H5v20h14V7l-5-5Zm0 0v6h5M8 12h8M8 16h6',
};
export function Icon({ name }: { name: keyof typeof paths }) {
  return (
    <svg
      className="ui-icon"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d={paths[name]} />
    </svg>
  );
}
export function Brand() {
  return (
    <>
      <span className="brand-mark">
        <Icon name="compass" />
      </span>
      <span className="brand-wordmark">
        IT-KOMPASS<small>Unternehmensplattform</small>
      </span>
    </>
  );
}
export function DensityControl() {
  const [compact, setCompact] = useState(() => {
    try {
      return localStorage.getItem('kompass-density') === 'compact';
    } catch {
      return false;
    }
  });
  function change() {
    const next = !compact;
    setCompact(next);
    document.documentElement.dataset.density = next ? 'compact' : 'comfortable';
    try {
      localStorage.setItem('kompass-density', next ? 'compact' : 'comfortable');
    } catch {
      /* Bedienung bleibt ohne lokalen Speicher verfügbar. */
    }
  }
  return (
    <button
      className="secondary density-control"
      aria-label="Kompakte Ansicht"
      aria-pressed={compact}
      onClick={change}
    >
      <Icon name="density" />
      <span>Kompakt</span>
    </button>
  );
}
export function TableToolbar({
  label,
  query,
  onQuery,
  count,
  total,
  children,
}: {
  label: string;
  query: string;
  onQuery: (value: string) => void;
  count: number;
  total: number;
  children?: ReactNode;
}) {
  return (
    <div className="table-toolbar">
      <label className="table-search">
        <Icon name="search" />
        <input
          type="search"
          aria-label={label}
          placeholder={label}
          value={query}
          onChange={(e) => onQuery(e.target.value)}
        />
      </label>
      {children}
      <span className="table-result" role="status">
        <strong>{count.toLocaleString('de-DE')}</strong> von {total.toLocaleString('de-DE')}{' '}
        geladenen Einträgen
      </span>
    </div>
  );
}

/** Kennzahlen beziehen sich nur auf die tatsächlich geladene Auswahl. */
export function WorkspaceSummary({
  items,
}: {
  items: { label: string; value: number | string; hint: string }[];
}) {
  return (
    <dl className="workspace-summary">
      {items.map((item, index) => (
        <div key={item.label}>
          <dt>
            <span aria-hidden="true">0{index + 1}</span>
            {item.label}
          </dt>
          <dd>
            {typeof item.value === 'number' ? item.value.toLocaleString('de-DE') : item.value}
          </dd>
          <small>{item.hint}</small>
        </div>
      ))}
    </dl>
  );
}

/** Springt innerhalb der Seite, ohne den Hash-Router oder Formularzustand zu verändern. */
export function SectionNav({ items }: { items: { id: string; label: string }[] }) {
  return (
    <nav className="section-nav" aria-label="Abschnitte des Datensatzes">
      {items.map((item, index) => (
        <button
          type="button"
          className="text-button"
          key={item.id}
          onClick={() => {
            const target = document.getElementById(item.id);
            if (target instanceof HTMLDetailsElement) target.open = true;
            target?.focus({ preventScroll: true });
            target?.scrollIntoView({ block: 'start' });
          }}
        >
          <span aria-hidden="true">0{index + 1}</span>
          {item.label}
        </button>
      ))}
    </nav>
  );
}
