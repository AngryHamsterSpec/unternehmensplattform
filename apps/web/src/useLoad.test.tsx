import { act, renderHook, waitFor } from '@testing-library/react';
import { afterEach, expect, test, vi } from 'vitest';
import { useLoad } from './useLoad';
import { request } from './api';

vi.mock('./api', async (original) => ({ ...(await original<object>()), request: vi.fn() }));
afterEach(() => vi.resetAllMocks());

test('Ein fehlgeschlagener neuer Abruf zeigt keine Daten des alten Pfads', async () => {
  vi.mocked(request)
    .mockResolvedValueOnce({ name: 'Organisation A' })
    .mockRejectedValueOnce(new Error('Nicht verfügbar'));
  const { result, rerender } = renderHook(({ path }) => useLoad<{ name: string }>(path), {
    initialProps: { path: '/a' },
  });
  await waitFor(() => expect(result.current.data?.name).toBe('Organisation A'));
  rerender({ path: '/b' });
  expect(result.current.data).toBeUndefined();
  await waitFor(() => expect(result.current.error).toBeInstanceOf(Error));
  expect(result.current.data).toBeUndefined();
});

test('Eine verspätete Antwort darf den neueren Pfad nicht überschreiben', async () => {
  let resolveOld!: (value: unknown) => void;
  vi.mocked(request)
    .mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          resolveOld = resolve;
        }),
    )
    .mockResolvedValueOnce({ name: 'Aktuell' });
  const { result, rerender } = renderHook(({ path }) => useLoad<{ name: string }>(path), {
    initialProps: { path: '/alt' },
  });
  rerender({ path: '/neu' });
  await waitFor(() => expect(result.current.data?.name).toBe('Aktuell'));
  await act(async () => resolveOld({ name: 'Veraltet' }));
  expect(result.current.data?.name).toBe('Aktuell');
});

test('Nach einer fehlgeschlagenen Aktualisierung bleibt kein alter Erfolg sichtbar', async () => {
  vi.mocked(request).mockResolvedValueOnce({ ok: true }).mockRejectedValueOnce(new Error('Fehler'));
  const { result, rerender } = renderHook(({ revision }) => useLoad('/a', revision), {
    initialProps: { revision: 0 },
  });
  await waitFor(() => expect(result.current.data).toEqual({ ok: true }));
  rerender({ revision: 1 });
  await waitFor(() => expect(result.current.error).toBeInstanceOf(Error));
  expect(result.current.data).toBeUndefined();
});
