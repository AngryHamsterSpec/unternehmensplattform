import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, expect, it, vi, afterEach } from 'vitest';
import { ScenarioForm } from './ScenarioForm';
import { decimal, money } from './format';
import type { Session } from './types';

const session: Session = {
  user: { id: 'test-user', display_name: 'Test' },
  organization: null,
  organizations: [],
  roles: ['ARCHITECTURE_ANALYST'],
  permissions: [],
  csrf_token: 'test-csrf',
  session_expires_at: '2026-09-10',
};
afterEach(() => vi.unstubAllGlobals());
describe('Szenarioeingabe', () => {
  it('unterscheidet unbekannte Mengen von null', () => {
    expect(decimal('')).toBeNull();
    expect(decimal('0')).toBe('0');
    expect(decimal('1,5')).toBe('1.5');
    expect(money(null)).toBe('Nicht berechenbar');
    expect(money('0')).toContain('0,00');
  });
  it('bewahrt unbekannte Fachwerte beim Speichern und sendet den CSRF-Header', async () => {
    const fetcher = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ id: 'saved' }) });
    vi.stubGlobal('fetch', fetcher);
    const saved = vi.fn();
    render(<ScenarioForm session={session} onSaved={saved} onCancel={vi.fn()} />);
    fireEvent.change(screen.getByLabelText('Szenarioname *'), { target: { value: 'Planung' } });
    fireEvent.change(screen.getByLabelText('Branche *'), { target: { value: 'Handwerk' } });
    fireEvent.change(screen.getByLabelText('Name der Arbeitslast 1 *'), {
      target: { value: 'Büro' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Szenario speichern' }));
    await waitFor(() => expect(fetcher).toHaveBeenCalledTimes(1));
    const options = fetcher.mock.calls[0][1] as RequestInit;
    const payload = JSON.parse(String(options.body));
    expect(payload.workloads[0].memory_gib).toBeNull();
    expect(payload.company_profile.monthly_budget).toBeNull();
    expect((options.headers as Headers).get('X-CSRF-Token')).toBe('test-csrf');
    expect(payload.organization_id).toBeUndefined();
    expect(saved).toHaveBeenCalledWith({ id: 'saved' });
  });
  it('zeigt einen Versionskonflikt, ohne ihn zu verschlucken', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: false,
        status: 409,
        json: async () => ({ detail: 'Das Szenario wurde inzwischen geändert.' }),
      }),
    );
    render(<ScenarioForm session={session} onSaved={vi.fn()} onCancel={vi.fn()} />);
    fireEvent.submit(screen.getByRole('button', { name: 'Szenario speichern' }).closest('form')!);
    expect(await screen.findAllByRole('alert')).toHaveLength(2);
    expect(screen.getAllByText('Das Szenario wurde inzwischen geändert.').length).toBeGreaterThan(
      0,
    );
  });
});
