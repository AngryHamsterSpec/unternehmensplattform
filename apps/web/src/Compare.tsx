import { useState } from 'react';
import { request } from './api';
import { Badge, Empty, ErrorNotice, Loading } from './components';
import { date, money, number, profiles } from './format';
import type { Assessment, Page } from './types';
import { useLoad } from './useLoad';

export function Compare({ navigate }: { navigate: (path: string) => void }) {
  const { data, error } = useLoad<Page<Assessment>>('/assessments?limit=100');
  const [extra, setExtra] = useState<Assessment[]>([]);
  const [cursor, setCursor] = useState<string | null | undefined>(undefined);
  const [selected, setSelected] = useState<string[]>([]);
  const [comparison, setComparison] = useState<Assessment[]>();
  const [pending, setPending] = useState(false);
  const [actionError, setActionError] = useState<unknown>();
  async function loadMore() {
    const next = cursor === undefined ? data?.next_cursor : cursor;
    if (!next) return;
    setPending(true);
    setActionError(undefined);
    try {
      const page = await request<Page<Assessment>>(
        '/assessments?limit=100&cursor=' + encodeURIComponent(next),
      );
      setExtra((v) => [...v, ...page.items]);
      setCursor(page.next_cursor);
    } catch (e) {
      setActionError(e);
    } finally {
      setPending(false);
    }
  }
  async function compare() {
    setPending(true);
    setActionError(undefined);
    try {
      setComparison(
        (await request<Page<Assessment>>('/assessments/compare?ids=' + selected.join(','))).items,
      );
    } catch (e) {
      setActionError(e);
    } finally {
      setPending(false);
    }
  }
  const all = [...(data?.items ?? []), ...extra];
  const versionsDiffer =
    comparison &&
    new Set(
      comparison.map((a) =>
        [
          a.cost_catalog_version,
          a.rule_set_version,
          a.candidate_catalog_version,
          a.horizon_months,
        ].join('|'),
      ),
    ).size > 1;
  return (
    <section>
      <header className="page-header">
        <div>
          <p className="eyebrow">Entscheidungsübersicht</p>
          <h1>Bewertungen vergleichen</h1>
          <p>
            Wähle bis zu fünf gespeicherte Bewertungen. Profilstand, Zeitraum und Regeln bleiben
            sichtbar.
          </p>
        </div>
        <button disabled={selected.length < 1 || pending} onClick={() => void compare()}>
          Auswahl vergleichen ({selected.length}/5)
        </button>
      </header>
      <ErrorNotice error={error ?? actionError} />
      {!data && !error ? (
        <Loading />
      ) : all.length === 0 ? (
        <Empty title="Noch keine Bewertungen">
          Erfasse zuerst ein Szenario und starte eine Bewertung.
        </Empty>
      ) : (
        <div className="form-card table-scroll">
          <table>
            <thead>
              <tr>
                <th>Auswahl</th>
                <th>Zeitpunkt</th>
                <th>Modus</th>
                <th>Zeitraum</th>
                <th>Status</th>
                <th>Details</th>
              </tr>
            </thead>
            <tbody>
              {all.map((a) => (
                <tr key={a.id}>
                  <td>
                    <input
                      type="checkbox"
                      aria-label={'Bewertung auswählen ' + a.id}
                      checked={selected.includes(a.id)}
                      disabled={pending || (!selected.includes(a.id) && selected.length >= 5)}
                      onChange={(e) => {
                        setSelected(
                          e.target.checked
                            ? [...selected, a.id]
                            : selected.filter((id) => id !== a.id),
                        );
                        setComparison(undefined);
                      }}
                    />
                  </td>
                  <th>{date(a.created_at)}</th>
                  <td>{profiles[a.options.weight_profile]}</td>
                  <td>{a.horizon_months} Monate</td>
                  <td>
                    <Badge value={a.status} />
                  </td>
                  <td>
                    <button className="text-button" onClick={() => navigate('/bewertung/' + a.id)}>
                      Öffnen
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {(cursor === undefined ? data?.next_cursor : cursor) && (
            <button className="secondary" disabled={pending} onClick={() => void loadMore()}>
              Weitere Bewertungen laden
            </button>
          )}
        </div>
      )}
      {comparison && (
        <section className="form-card">
          <h2>Vergleich der gespeicherten Ergebnisse</h2>
          {versionsDiffer && (
            <div className="notice warning">
              Zeitraum oder Katalog-/Regelstand unterscheiden sich. Die Gesamtkosten sind dadurch
              nur eingeschränkt direkt vergleichbar.
            </div>
          )}
          <div className="table-scroll">
            <table className="comparison">
              <thead>
                <tr>
                  <th>Merkmal</th>
                  {comparison.map((a) => (
                    <th key={a.id}>
                      {profiles[a.options.weight_profile]}
                      <small>{date(a.created_at)}</small>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                <tr>
                  <th>Profilversion</th>
                  {comparison.map((a) => (
                    <td key={a.id}>
                      <code>{a.scenario_version_id}</code>
                    </td>
                  ))}
                </tr>
                <tr>
                  <th>Status</th>
                  {comparison.map((a) => (
                    <td key={a.id}>
                      <Badge value={a.status} />
                    </td>
                  ))}
                </tr>
                <tr>
                  <th>Empfehlung</th>
                  {comparison.map((a) => (
                    <td key={a.id}>
                      {a.candidates.find((c) => c.key === a.recommended_candidate_key)?.label ??
                        'Keine bestätigt'}
                    </td>
                  ))}
                </tr>
                <tr>
                  <th>Betrachtung</th>
                  {comparison.map((a) => (
                    <td key={a.id}>{a.horizon_months} Monate</td>
                  ))}
                </tr>
                {(['SAAS', 'PAAS', 'IAAS', 'HYBRID'] as const).map((plan) => (
                  <tr key={plan}>
                    <th>{plan} · Punkte / TCO</th>
                    {comparison.map((a) => {
                      const c = a.candidates.find((c) => c.key === plan);
                      return (
                        <td key={a.id}>
                          {c ? (
                            <>
                              <Badge value={c.status} />
                              <p>
                                {number(c.score)} / {money(c.costs.tco_total)}
                              </p>
                            </>
                          ) : (
                            'Nicht enthalten'
                          )}
                        </td>
                      );
                    })}
                  </tr>
                ))}
                <tr>
                  <th>Regeln</th>
                  {comparison.map((a) => (
                    <td key={a.id}>{a.rule_set_version}</td>
                  ))}
                </tr>
                <tr>
                  <th>Kostenkatalog</th>
                  {comparison.map((a) => (
                    <td key={a.id}>{a.cost_catalog_version}</td>
                  ))}
                </tr>
              </tbody>
            </table>
          </div>
        </section>
      )}
    </section>
  );
}
