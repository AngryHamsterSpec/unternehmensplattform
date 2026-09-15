import { afterEach, expect, it, vi } from 'vitest';
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { SourceImport } from './DataIntelligence';
import type { TaskView } from './generated/domain';
import type { Session } from './types';

const session: Session = {
  user: { id: 'actor', display_name: 'Test' },
  organization: null,
  organizations: [],
  roles: ['ARCHITECTURE_ANALYST'],
  csrf_token: 'test',
  permissions: [],
  session_expires_at: '2026-09-14',
};
function task(id: string): TaskView {
  return {
    id,
    created_by_user_id: 'actor',
    dataset_id: null,
    version_no: null,
    kind: 'SOURCE',
    status: 'SUCCEEDED',
    progress: 100,
    message: 'Abgeschlossen',
    error: null,
    result_hash: 'a'.repeat(64),
    created_at: '2026-09-14T10:00:00Z',
    finished_at: '2026-09-14T10:00:01Z',
    request: {},
    result: { dataset_id: id, job_id: id, original_hash: 'a'.repeat(64), source: {} },
  };
}
afterEach(() => vi.unstubAllGlobals());

it('öffnet nach einem neuen Import niemals versehentlich das vorherige Ergebnis', async () => {
  const previous = task('previous');
  const next = task('next');
  let resolveCreation: (value: unknown) => void = () => undefined;
  const creation = new Promise((resolve) => {
    resolveCreation = resolve;
  });
  let resolveDetail: (value: unknown) => void = () => undefined;
  const detail = new Promise((resolve) => {
    resolveDetail = resolve;
  });
  vi.stubGlobal(
    'fetch',
    vi.fn().mockImplementation(async (path: string) => {
      if (path === '/api/v1/data-sources/import') return { ok: true, json: async () => creation };
      if (path === '/api/v1/data-tasks/next') return { ok: true, json: async () => detail };
      const value =
        path === '/api/v1/data-sources'
          ? {
              items: [
                { id: 'source', name: 'Quelle', provider: 'postgresql', tables: ['demo.sales'] },
              ],
              live_ai_available: false,
            }
          : path.startsWith('/api/v1/data-tasks?')
            ? { items: [previous], next_cursor: null }
            : previous;
      return { ok: true, json: async () => value };
    }),
  );
  const navigate = vi.fn();
  const { container } = render(<SourceImport session={session} navigate={navigate} />);
  container.querySelector('details')!.open = true;
  await screen.findByRole('button', { name: 'Importierten Datensatz öffnen' });
  fireEvent.change(screen.getByLabelText('Name des Datenbanksnapshots'), {
    target: { value: 'Neuer Snapshot' },
  });
  fireEvent.click(screen.getByRole('button', { name: 'Datenbanksnapshot importieren' }));
  await waitFor(() =>
    expect(
      screen.queryByRole('button', { name: 'Importierten Datensatz öffnen' }),
    ).not.toBeInTheDocument(),
  );
  await act(async () => resolveCreation({ ...next, status: 'QUEUED', result: null }));
  expect(
    screen.queryByRole('button', { name: 'Importierten Datensatz öffnen' }),
  ).not.toBeInTheDocument();
  await act(async () => resolveDetail(next));
  fireEvent.click(await screen.findByRole('button', { name: 'Importierten Datensatz öffnen' }));
  expect(navigate).toHaveBeenCalledExactlyOnceWith('/daten/next');
});
