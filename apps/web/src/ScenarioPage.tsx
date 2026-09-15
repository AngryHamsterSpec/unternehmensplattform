import { useRef, useState } from 'react';
import type { FormEvent } from 'react';
import { request } from './api';
import { Badge, Empty, ErrorNotice, Field, Loading } from './components';
import { date, groupKeys, groups, money, profiles } from './format';
import type { Assessment, Options, Page, Scenario, Session, Version } from './types';
import { ScenarioForm } from './ScenarioForm';
import { useLoad } from './useLoad';

export function ScenarioPage({
  id,
  session,
  navigate,
}: {
  id: string;
  session: Session;
  navigate: (path: string) => void;
}) {
  const [revision, setRevision] = useState(0);
  const [editing, setEditing] = useState(false);
  const { data, error } = useLoad<Scenario>('/scenarios/' + id, revision);
  if (error) return <ErrorNotice error={error} />;
  if (!data) return <Loading />;
  if (editing)
    return (
      <ScenarioForm
        key={data.current_version}
        scenario={data}
        session={session}
        onCancel={() => setEditing(false)}
        onSaved={() => {
          setEditing(false);
          setRevision((v) => v + 1);
        }}
      />
    );
  return (
    <ScenarioView
      key={data.current_version}
      scenario={data}
      session={session}
      onEdit={() => setEditing(true)}
      navigate={navigate}
    />
  );
}

function ScenarioView({
  scenario,
  session,
  onEdit,
  navigate,
}: {
  scenario: Scenario;
  session: Session;
  onEdit: () => void;
  navigate: (path: string) => void;
}) {
  const canWrite = session.roles.some(
    (role) => role === 'ORG_ADMIN' || role === 'ARCHITECTURE_ANALYST',
  );
  const [version, setVersion] = useState<Version>(scenario.version);
  const [options, setOptions] = useState<Options>({
    weight_profile: 'ECONOMIC',
    custom_weights: null,
    horizon_months: 36,
  });
  const [weights, setWeights] = useState({
    cost: '35',
    performance: '15',
    resilience: '20',
    operations: '20',
    governance: '10',
  });
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<unknown>();
  const { data: assessments, error: assessmentError } = useLoad<Page<Assessment>>(
    '/assessments?scenario_id=' + scenario.id + '&limit=100',
  );
  const attempt = useRef<{ json: string; key: string } | null>(null);
  async function selectVersion(value: string) {
    setPending(true);
    setError(undefined);
    try {
      setVersion(await request<Version>('/scenarios/' + scenario.id + '/versions/' + value));
    } catch (e) {
      setError(e);
    } finally {
      setPending(false);
    }
  }
  async function assess(event: FormEvent) {
    event.preventDefault();
    setPending(true);
    setError(undefined);
    const body = {
      ...options,
      custom_weights: options.weight_profile === 'CUSTOM' ? weights : null,
      scenario_version_id: version.id,
    };
    const json = JSON.stringify(body);
    if (attempt.current?.json !== json) attempt.current = { json, key: crypto.randomUUID() };
    try {
      const result = await request<Assessment>('/assessments', {
        method: 'POST',
        csrf: session.csrf_token,
        body,
        idempotencyKey: attempt.current.key,
      });
      navigate('/bewertung/' + result.id);
    } catch (e) {
      setError(e);
    } finally {
      setPending(false);
    }
  }
  const input = version.data;
  return (
    <section>
      <header className="page-header">
        <div>
          <p className="eyebrow">Gespeichertes Szenario</p>
          <h1>{scenario.name}</h1>
          <p>
            {input.company_profile.industry} · {input.workloads.length} Arbeitslast(en) · Version{' '}
            {version.version_no}
          </p>
        </div>
        {canWrite && (
          <button className="secondary" onClick={onEdit} disabled={pending}>
            Szenario bearbeiten
          </button>
        )}
      </header>
      <ErrorNotice error={error} />
      <div className="metric-grid">
        <div>
          <small>Monatlicher Rahmen</small>
          <strong>{money(input.company_profile.monthly_budget)}</strong>
        </div>
        <div>
          <small>Einmaliger Rahmen</small>
          <strong>{money(input.company_profile.initial_budget)}</strong>
        </div>
        <div>
          <small>Gespeicherte Versionen</small>
          <strong>{scenario.versions.length}</strong>
        </div>
      </div>
      <section className="form-card">
        <div className="section-heading">
          <h2>Unveränderlicher Profilstand</h2>
          <Field label="Profilversion">
            <select
              value={version.version_no}
              disabled={pending}
              onChange={(e) => void selectVersion(e.target.value)}
            >
              {scenario.versions.map((v) => (
                <option key={v.id} value={v.version_no}>
                  Version {v.version_no} · {date(v.created_at)}
                </option>
              ))}
            </select>
          </Field>
        </div>
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Arbeitslast</th>
                <th>Nutzende</th>
                <th>vCPU</th>
                <th>RAM (GiB)</th>
                <th>Speicher (GiB)</th>
              </tr>
            </thead>
            <tbody>
              {input.workloads.map((w) => (
                <tr key={w.workload_key}>
                  <th>{w.name}</th>
                  <td>{w.user_count ?? 'Unbekannt'}</td>
                  <td>{w.vcpu_count ?? 'Unbekannt'}</td>
                  <td>{w.memory_gib ?? 'Unbekannt'}</td>
                  <td>{w.storage_gib ?? 'Unbekannt'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <details>
          <summary>Alle ursprünglichen Eingaben ansehen</summary>
          <pre>{JSON.stringify(input, null, 2)}</pre>
        </details>
      </section>
      {canWrite && (
        <form className="form-card" onSubmit={(event) => void assess(event)}>
          <h2>Architektur bewerten</h2>
          <p>
            Harte Anforderungen werden vor der Punktewertung geprüft. Unbekannte Werte bleiben
            sichtbar.
          </p>
          <fieldset disabled={pending}>
            <div className="form-grid">
              <Field label="Bewertungsmodus">
                <select
                  value={options.weight_profile}
                  onChange={(e) =>
                    setOptions({
                      ...options,
                      weight_profile: e.target.value as Options['weight_profile'],
                    })
                  }
                >
                  {Object.entries(profiles).map(([key, label]) => (
                    <option key={key} value={key}>
                      {label}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label="Betrachtungszeitraum (Monate)">
                <input
                  type="number"
                  min={1}
                  max={120}
                  required
                  value={options.horizon_months}
                  onChange={(e) =>
                    setOptions({ ...options, horizon_months: Number(e.target.value) })
                  }
                />
              </Field>
            </div>
            {options.weight_profile === 'CUSTOM' && (
              <div className="form-grid">
                {groupKeys.map((group) => (
                  <Field key={group} label={groups[group] + ' · relatives Gewicht'}>
                    <input
                      type="number"
                      min="0"
                      step="any"
                      required
                      value={weights[group]}
                      onChange={(e) => setWeights({ ...weights, [group]: e.target.value })}
                    />
                  </Field>
                ))}
                <p className="form-hint">
                  Der Server normiert die Gewichte. Mindestens ein Gewicht muss größer als null
                  sein.
                </p>
              </div>
            )}
            <div className="form-actions">
              <p>Synthetischer EU-Katalog · vier Kandidatenpläne</p>
              <button type="submit">
                {pending ? 'Bewertung wird berechnet …' : 'Bewertung starten'}
              </button>
            </div>
          </fieldset>
        </form>
      )}
      <section className="form-card">
        <h2>Gespeicherte Bewertungen</h2>
        <ErrorNotice error={assessmentError} />
        {!assessments ? (
          <Loading />
        ) : assessments.items.length === 0 ? (
          <Empty title="Noch keine Bewertung">
            Bewerte einen Profilstand, um die Alternativen zu vergleichen.
          </Empty>
        ) : (
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Zeitpunkt</th>
                  <th>Modus</th>
                  <th>Ergebnis</th>
                  <th>Details</th>
                </tr>
              </thead>
              <tbody>
                {assessments.items.map((a) => (
                  <tr key={a.id}>
                    <th>{date(a.created_at)}</th>
                    <td>{profiles[a.options.weight_profile]}</td>
                    <td>
                      <Badge value={a.status} />
                    </td>
                    <td>
                      <button
                        className="text-button"
                        onClick={() => navigate('/bewertung/' + a.id)}
                      >
                        Bewertung öffnen
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {assessments?.next_cursor && (
          <p>Weitere Bewertungen sind in der vollständigen Vergleichsliste verfügbar.</p>
        )}
      </section>
    </section>
  );
}
