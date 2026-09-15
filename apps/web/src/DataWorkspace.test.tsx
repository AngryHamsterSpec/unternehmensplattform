import { afterEach, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { DataWorkspace, ImportForm, ProfilePanel } from './DataWorkspace';
import type { Session } from './types';
import type { DataProfile } from './generated/domain';

const session: Session = {
  user: { id: 'test', display_name: 'Test' },
  organization: null,
  organizations: [],
  roles: ['VIEWER'],
  csrf_token: 'test',
  permissions: [],
  session_expires_at: '2026-09-11',
};
afterEach(() => vi.unstubAllGlobals());

it('öffnet den Import gezielt und bewahrt Eingaben beim Zuklappen', async () => {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue({ ok: true, json: async () => ({ items: [] }) }),
  );
  const { container } = render(
    <DataWorkspace session={{ ...session, roles: ['ARCHITECTURE_ANALYST'] }} navigate={vi.fn()} />,
  );
  await screen.findByText('Noch keine Datensätze');
  const panel = container.querySelector('.import-disclosure') as HTMLDetailsElement;
  expect(panel.open).toBe(false);
  fireEvent.click(screen.getByRole('button', { name: 'Datei importieren' }));
  expect(panel.open).toBe(true);
  const name = screen.getByLabelText('Datensatzname');
  expect(name).toHaveFocus();
  fireEvent.change(name, { target: { value: 'Mein Entwurf' } });
  fireEvent.click(panel.querySelector('summary')!);
  fireEvent.click(screen.getByRole('button', { name: 'Datei importieren' }));
  expect(name).toHaveValue('Mein Entwurf');
});

it('kombiniert Bestandsfilter, ohne unveröffentlichte Importe als laufend auszugeben', async () => {
  const items = [
    {
      id: 'a',
      name: 'Umsatz',
      filename: 'umsatz.csv',
      current_version: 2,
      created_at: '2026-09-13T10:00:00Z',
    },
    {
      id: 'b',
      name: 'Import prüfen',
      filename: 'bestand.xlsx',
      current_version: null,
      created_at: '2026-09-13T10:00:00Z',
    },
  ];
  vi.stubGlobal(
    'fetch',
    vi.fn().mockImplementation(async (path: string) => ({
      ok: true,
      json: async () =>
        path === '/api/v1/datasets'
          ? { items }
          : { items: [], next_cursor: null, live_ai_available: false },
    })),
  );
  render(<DataWorkspace session={session} navigate={vi.fn()} />);
  await screen.findByRole('rowheader', { name: 'Umsatz' });
  fireEvent.change(screen.getByLabelText('Datenstand'), { target: { value: 'pending' } });
  expect(screen.queryByRole('rowheader', { name: 'Umsatz' })).not.toBeInTheDocument();
  expect(screen.getByRole('rowheader', { name: 'Import prüfen' })).toBeVisible();
  fireEvent.change(screen.getByRole('searchbox'), { target: { value: 'umsatz' } });
  expect(screen.getByText('Keine geladenen Datensätze passen zum Filter.')).toBeVisible();
  expect(screen.getByRole('status')).toHaveTextContent('0 von 2 geladenen Einträgen');
});

it('zeigt für Lesekonten keinen Import', async () => {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue({ ok: true, json: async () => ({ items: [] }) }),
  );
  render(<DataWorkspace session={session} navigate={vi.fn()} />);
  expect(await screen.findByText('Noch keine Datensätze')).toBeVisible();
  expect(screen.queryByRole('button', { name: 'CSV importieren' })).not.toBeInTheDocument();
});

it('verlangt eine Datei vor dem Import', () => {
  const imported = vi.fn();
  render(<ImportForm session={session} onImported={imported} />);
  expect(screen.getByRole('button', { name: 'CSV importieren' })).toBeDisabled();
  fireEvent.click(screen.getByRole('button', { name: 'Synthetische CSV laden' }));
  expect(screen.getByRole('button', { name: 'CSV importieren' })).toBeEnabled();
  expect(screen.getByLabelText('Datensatzname')).toHaveValue('Synthetische Abteilungsdaten');
  expect(imported).not.toHaveBeenCalled();
});

it('wechselt die sichtbare Verteilung und rendert Dateiinhalte ausschließlich als Text', () => {
  const profile: DataProfile = {
    rows: 2,
    columns: [
      {
        name: 'A',
        inferred_type: 'text',
        missing: 0,
        distinct: 1,
        top_values: [{ value: '<img src=x onerror=alert(1)>', count: 2 }],
        minimum: null,
        maximum: null,
        mean: null,
        outliers: null,
      },
      {
        name: 'B',
        inferred_type: 'text',
        missing: 0,
        distinct: 1,
        top_values: [{ value: 'Berlin', count: 2 }],
        minimum: null,
        maximum: null,
        mean: null,
        outliers: null,
      },
    ],
    missing_cells: 0,
    duplicate_rows: 1,
    completeness_percent: '100.00',
    sample: [],
    profiling_version: 'csv-profile-1',
    pipeline_version: 'csv-transform-1',
    statistics_note: '',
    import_info: null,
    source_format: 'csv',
    source_worksheet: null,
    source_table: null,
    database_source: null,
  };
  const { container } = render(<ProfilePanel profile={profile} />);
  expect(screen.getByText('<img src=x onerror=alert(1)>')).toBeVisible();
  expect(container.querySelector('img')).toBeNull();
  fireEvent.change(screen.getByLabelText('Verteilung für Spalte'), { target: { value: 'B' } });
  expect(screen.getByText('Berlin')).toBeVisible();
  expect(screen.queryByText('<img src=x onerror=alert(1)>')).not.toBeInTheDocument();
});

it('überträgt große Dateien als Blob-Abschnitte und setzt nach einem Verbindungsfehler fort', async () => {
  localStorage.clear();
  const imported = vi.fn();
  const bytes = 4194304 + 16;
  const file = new File([new Uint8Array(bytes)], 'gross.csv');
  const obj = {
    id: 'upload-a',
    name: 'Groß',
    filename: file.name,
    delimiter: ';',
    expected_bytes: bytes,
    received_bytes: 0,
    chunk_count: 0,
    chunk_bytes: 4194304,
    status: 'OPEN',
  };
  let disconnected = true;
  const sent: number[] = [];
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string, options: RequestInit) => {
      let body: unknown = { items: [] };
      if (options.method === 'POST' && url.endsWith('/data-uploads')) body = obj;
      if (url.includes('/chunks/')) {
        const blob = options.body as Blob;
        sent.push(blob.size);
        expect(options.headers).toBeInstanceOf(Headers);
        expect((options.headers as Headers).get('X-CSRF-Token')).toBe('test');
        if (disconnected) {
          disconnected = false;
          throw new TypeError('Verbindung unterbrochen');
        }
        const ordinal = Number(url.split('/').at(-1));
        body = {
          ...obj,
          received_bytes: Math.min(bytes, (ordinal + 1) * 4194304),
          chunk_count: ordinal + 1,
        };
      }
      if (url.endsWith('/complete')) body = { id: 'job-a', dataset_id: 'dataset-a' };
      return { ok: true, status: 200, json: async () => body };
    }),
  );
  render(<ImportForm session={session} onImported={imported} />);
  fireEvent.change(screen.getByLabelText('Datensatzname'), { target: { value: 'Groß' } });
  fireEvent.change(screen.getByLabelText(/^Datendatei/), { target: { files: [file] } });
  fireEvent.click(screen.getByRole('button', { name: 'CSV importieren' }));
  expect(await screen.findByRole('button', { name: 'Upload fortsetzen' })).toBeEnabled();
  fireEvent.click(screen.getByRole('button', { name: 'Upload fortsetzen' }));
  await waitFor(() =>
    expect(imported).toHaveBeenCalledWith({ id: 'job-a', dataset_id: 'dataset-a' }),
  );
  expect(sent).toEqual([4194304, 4194304, 16]);
  localStorage.clear();
});
