import { useRef, useState } from 'react';
import { request } from './api';
import { Badge, ErrorNotice, Loading } from './components';
import { date, groupKeys, groups, money, number, profiles } from './format';
import type { Assessment, Candidate, Page, Session } from './types';
import { useLoad } from './useLoad';

const axes: Record<string, string> = {
  SELF_MANAGED: 'Eigenbetrieb',
  PUBLIC_CLOUD: 'Öffentliche Cloud',
  PRIVATE_CLOUD: 'Private Cloud',
  TRADITIONAL: 'Klassischer Betrieb',
  ON_PREMISES: 'Eigener Standort',
  PROVIDER: 'Anbieterstandort',
  PRIMARY: 'Primärsystem',
  BACKUP: 'Sicherung',
};

function CandidateDetails({ candidate: c, result }: { candidate: Candidate; result: Assessment }) {
  return (
    <article className="candidate-detail">
      <div className="section-heading">
        <h3>{c.label}</h3>
        <Badge value={c.status} />
      </div>
      <p>{c.explanation}</p>
      <h4>Zuordnung der Arbeitslasten</h4>
      {c.assignments.map((a) => (
        <div className="assignment" key={a.workload_key}>
          <strong>{a.workload_key}</strong>
          <p>{a.explanation}</p>
          <div className="axis-grid">
            <span>
              <small>Servicemodell</small>
              {axes[a.service_model] ?? a.service_model}
            </span>
            <span>
              <small>Deployment</small>
              {axes[a.deployment_model] ?? a.deployment_model}
            </span>
            <span>
              <small>Hostingort</small>
              {axes[a.hosting_location] ?? a.hosting_location}
            </span>
          </div>
          {a.components.length > 0 && (
            <ul>
              {a.components.map((component, i) => (
                <li key={i}>
                  {axes[component.role] ?? component.role}:{' '}
                  {axes[component.service_model] ?? component.service_model} ·{' '}
                  {axes[component.deployment_model] ?? component.deployment_model} ·{' '}
                  {axes[component.hosting_location] ?? component.hosting_location}
                </li>
              ))}
            </ul>
          )}
        </div>
      ))}
      <h4>Prüfung der Anforderungen</h4>
      <ul className="constraints">
        {c.constraints.map((item) => (
          <li key={item.key}>
            <Badge value={item.status} />
            <div>
              {item.explanation}
              <small>Nachweise: {item.evidence_ids.join(', ')}</small>
            </div>
          </li>
        ))}
      </ul>
      <h4>Kriterien und gewichteter Beitrag</h4>
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th>Kriterium</th>
              <th>Punkte / 100</th>
              <th>Gewicht</th>
              <th>Beitrag zum Gesamtwert</th>
            </tr>
          </thead>
          <tbody>
            {groupKeys.map((group) => (
              <tr key={group}>
                <th>{groups[group]}</th>
                <td>{number(c.criterion_scores[group])}</td>
                <td>{number(Number(result.weights[group]) * 100)} %</td>
                <td>
                  {c.criterion_scores[group] === null
                    ? 'Unbekannt'
                    : number(Number(c.criterion_scores[group]) * Number(result.weights[group]))}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="form-hint">
        Beiträge sind eine Anzeige der gespeicherten Kriterien und Gewichte. Maßgeblich ist der vom
        Server geprüfte Gesamtwert.
      </p>
      <h4>Kosten über {result.horizon_months} Monate</h4>
      <div className="metric-grid compact">
        <div>
          <small>Einmalige Kosten</small>
          <strong>{money(c.costs.startup_total)}</strong>
        </div>
        <div>
          <small>Monatliche Kosten</small>
          <strong>{money(c.costs.monthly_total)}</strong>
        </div>
        <div>
          <small>Gesamtkosten / TCO</small>
          <strong>{money(c.costs.tco_total)}</strong>
        </div>
      </div>
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th>Kostenposition</th>
              <th>Art</th>
              <th>Menge</th>
              <th>Einzelpreis</th>
              <th>Zeitraum</th>
              <th>Gesamt</th>
            </tr>
          </thead>
          <tbody>
            {c.costs.lines.map((line) => (
              <tr key={line.id}>
                <th>
                  {line.label}
                  <small>
                    {line.price_id} · {line.evidence_ids.join(', ')}
                  </small>
                </th>
                <td>{line.category}</td>
                <td>{number(line.quantity)}</td>
                <td>{money(line.unit_price)}</td>
                <td>
                  {line.recurrence === 'ONCE' ? 'Einmalig' : result.horizon_months + ' Monate'}
                </td>
                <td>{money(line.total)}</td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr>
              <th colSpan={5}>Investitionskosten / CAPEX</th>
              <td>{money(c.costs.capex_total)}</td>
            </tr>
            <tr>
              <th colSpan={5}>Betriebskosten / OPEX</th>
              <td>{money(c.costs.opex_total)}</td>
            </tr>
          </tfoot>
        </table>
      </div>
      {c.uncertainties.length > 0 && (
        <div className="notice warning">
          <strong>Offene Angaben und Unsicherheit</strong>
          <ul>
            {c.uncertainties.map((text, i) => (
              <li key={i}>{text}</li>
            ))}
          </ul>
        </div>
      )}
      {c.assumptions.length > 0 && (
        <details>
          <summary>Annahmen dieses Plans</summary>
          <ul>
            {c.assumptions.map((text, i) => (
              <li key={i}>{text}</li>
            ))}
          </ul>
        </details>
      )}
    </article>
  );
}

interface Explanation {
  id: string;
  status: string;
  failure_code: string | null;
  model: string;
  notice: string;
  output: { summary: string; evidence_ids: string[] } | null;
}
function Explanations({ result, session }: { result: Assessment; session: Session }) {
  const [revision, setRevision] = useState(0);
  const { data, error: loadError } = useLoad<Page<Explanation>>(
    '/assessments/' + result.id + '/explanations',
    revision,
  );
  const [error, setError] = useState<unknown>();
  const [pending, setPending] = useState(false);
  const attempt = useRef<string | null>(null);
  async function explain() {
    setPending(true);
    setError(undefined);
    attempt.current ??= crypto.randomUUID();
    try {
      await request('/assessments/' + result.id + '/explanations', {
        method: 'POST',
        csrf: session.csrf_token,
        idempotencyKey: attempt.current,
        body: { approve_external_processing: true },
      });
      setRevision((value) => value + 1);
      attempt.current = null;
    } catch (e) {
      setError(e);
    } finally {
      setPending(false);
    }
  }
  return (
    <section className="form-card">
      <h2>Optionale KI-Erklärung</h2>
      <button className="text-button" onClick={() => setRevision((value) => value + 1)}>
        Anfragestatus aktualisieren
      </button>
      <p>
        Übertragen werden nur Bewertungsstatus, Punkte, Gewichte, Kosten und Katalogkennungen an
        OpenAI. Unternehmensnamen und freie Eingabetexte werden ausgelassen. Die geprüfte
        Modellrechnung bleibt maßgeblich.
      </p>
      <ErrorNotice error={error ?? loadError} />
      {data?.items.map((item) => (
        <div className="notice info" key={item.id}>
          <strong>
            {item.status === 'SUCCEEDED'
              ? 'KI-Formulierung · ' + item.model
              : item.status === 'FAILED'
                ? 'KI-Erklärung fehlgeschlagen'
                : item.status === 'INDETERMINATE'
                  ? 'Externer Ausgang unbekannt – Budget bleibt reserviert'
                  : 'Aufruf reserviert – noch kein bestätigter Abschluss'}
          </strong>
          <p>
            {item.output?.summary ??
              'Die ursprüngliche Bewertung bleibt vollständig verfügbar. Ein unklarer Aufruf wird nicht automatisch wiederholt.'}
          </p>
          {item.output && <small>Verweise: {item.output.evidence_ids.join(', ')}</small>}
        </div>
      ))}
      {session.openai_available &&
      session.roles.some((r) => r !== 'VIEWER') &&
      result.status === 'VERIFIED' ? (
        <button className="secondary" onClick={() => void explain()} disabled={pending}>
          {pending ? 'Erklärung wird angefragt …' : 'Übertragung zustimmen und Erklärung anfordern'}
        </button>
      ) : (
        <p className="muted">
          Für diese Sitzung ist keine externe Verarbeitung freigegeben. Die regelbasierte Erklärung
          ist oben verfügbar.
        </p>
      )}
    </section>
  );
}

export function Result({
  result,
  session,
  onBack,
}: {
  result: Assessment;
  session?: Session;
  onBack?: () => void;
}) {
  const recommended = result.candidates.find((c) => c.key === result.recommended_candidate_key);
  return (
    <section>
      <header className="page-header">
        <div>
          <p className="eyebrow">
            Architekturentscheidung · {profiles[result.options.weight_profile]}
          </p>
          <h1>Bewertung im Detail</h1>
          <p>
            {date(result.created_at)} · {result.horizon_months} Monate ·{' '}
            <Badge value={result.status} />
          </p>
        </div>
        {onBack && (
          <button className="secondary" onClick={onBack}>
            Zurück zur Übersicht
          </button>
        )}
      </header>
      <div className={'recommendation ' + (recommended ? '' : 'unresolved')}>
        <p className="eyebrow">
          {recommended ? 'Empfehlung im synthetischen Modell' : 'Keine bestätigte Empfehlung'}
        </p>
        <h2>
          {recommended?.label ??
            (result.status === 'NO_FEASIBLE_OPTION'
              ? 'Keine Alternative erfüllt alle Anforderungen.'
              : 'Die Grundlage reicht noch nicht aus.')}
        </h2>
        <p>{result.explanation}</p>
        {recommended && (
          <div className="recommendation-values">
            <strong>
              {number(recommended.score)}
              <small>von 100 Punkten</small>
            </strong>
            <strong>
              {money(recommended.costs.tco_total)}
              <small>Gesamtkosten im Zeitraum</small>
            </strong>
          </div>
        )}
      </div>
      <div className="notice info">
        Alle Preise und Kapazitätszusagen stammen aus einem synthetischen Demo-Katalog. Sie sind
        keine Angebote realer Anbieter.
      </div>
      <section className="form-card">
        <h2>Die vier Alternativen</h2>
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Plan</th>
                <th>Eignung</th>
                <th>Punkte</th>
                <th>TCO</th>
                <th>Rang</th>
              </tr>
            </thead>
            <tbody>
              {result.candidates.map((c) => (
                <tr key={c.key} className={c.key === recommended?.key ? 'recommended-row' : ''}>
                  <th>{c.label}</th>
                  <td>
                    <Badge value={c.status} />
                  </td>
                  <td>
                    <span className="score-cell">
                      {number(c.score)}
                      {c.score !== null && (
                        <progress
                          max={100}
                          value={Number(c.score)}
                          aria-label={'Punkte ' + c.label}
                        />
                      )}
                    </span>
                  </td>
                  <td>{money(c.costs.tco_total)}</td>
                  <td>{c.rank ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
      {result.candidates.map((c) => (
        <details className="form-card" key={c.key} open={c.key === recommended?.key}>
          <summary>{c.label} · Anforderungen, Kosten und Begründung</summary>
          <CandidateDetails candidate={c} result={result} />
        </details>
      ))}
      <section className="form-card">
        <h2>Wie stabil ist die Empfehlung?</h2>
        <p>{result.sensitivity.explanation}</p>
        <p>
          {result.sensitivity.tested_variations} Gewichtsvariationen ·{' '}
          {result.sensitivity.winner_changes} Wechsel · Punkteabstand{' '}
          {number(result.sensitivity.score_gap)}
        </p>
        <details>
          <summary>Sensitivitätsprüfung ansehen</summary>
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Kriterium</th>
                  <th>Faktor</th>
                  <th>Beste Alternative</th>
                  <th>Wechsel</th>
                </tr>
              </thead>
              <tbody>
                {result.sensitivity.variations.map((v, i) => (
                  <tr key={i}>
                    <th>{groups[v.group]}</th>
                    <td>{number(v.factor)}</td>
                    <td>{v.winner_key ?? 'Keine'}</td>
                    <td>{v.changed ? 'Ja' : 'Nein'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </details>
      </section>
      <section className="form-card">
        <h2>Prüfung und Nachweise</h2>
        <Badge value={result.verification.valid ? 'VERIFIED' : 'VERIFICATION_FAILED'} />
        <ul>
          {result.verification.checks.map((text, i) => (
            <li key={i}>{text}</li>
          ))}
          {result.verification.errors.map((text, i) => (
            <li key={'error' + i}>{text}</li>
          ))}
        </ul>
        <dl className="version-list">
          <dt>Regeln</dt>
          <dd>{result.rule_set_version}</dd>
          <dt>Kandidatenkatalog</dt>
          <dd>{result.candidate_catalog_version}</dd>
          <dt>Kostenkatalog</dt>
          <dd>{result.cost_catalog_version}</dd>
          <dt>Ergebnishash</dt>
          <dd>
            <code>{result.result_hash}</code>
          </dd>
        </dl>
        <details>
          <summary>Alle Evidenzquellen ({result.evidence.length})</summary>
          {result.evidence.map((item) => (
            <article className="evidence" key={item.id}>
              <h4>{item.label}</h4>
              <p>
                <code>{item.id}</code> · {item.kind} · {item.version}
              </p>
              <p>{item.source}</p>
              <pre>{JSON.stringify(item.value, null, 2)}</pre>
            </article>
          ))}
        </details>
        <details>
          <summary>Annahmen und offene Punkte</summary>
          <ul>
            {[...result.assumptions, ...result.uncertainties].map((text, i) => (
              <li key={i}>{text}</li>
            ))}
          </ul>
        </details>
      </section>
      {session && <Explanations result={result} session={session} />}
    </section>
  );
}

export function ResultPage({
  id,
  session,
  onBack,
}: {
  id: string;
  session: Session;
  onBack: () => void;
}) {
  const { data, error } = useLoad<Assessment>('/assessments/' + id);
  if (error) return <ErrorNotice error={error} />;
  if (!data) return <Loading />;
  return <Result result={data} session={session} onBack={onBack} />;
}
