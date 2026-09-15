import { lazy, Suspense, useEffect, useState } from 'react';
import type { FormEvent, ReactNode } from 'react';
import { request } from './api';
import { ErrorNotice, Field, Loading } from './components';
import { date } from './format';
import { useLoad } from './useLoad';
import type { Session } from './types';
import type {
  AnalysisResult,
  JobView,
  PlanResult,
  QualityRule,
  RuleSetView,
  SourceCatalog,
  TaskSummary,
  TaskView,
  VersionView,
} from './generated/domain';

const AnalysisCharts = lazy(() => import('./AnalysisCharts'));

const labels: Record<TaskView['status'], string> = {
  QUEUED: 'Vorgemerkt',
  RUNNING: 'In Bearbeitung',
  SUCCEEDED: 'Abgeschlossen',
  FAILED: 'Fehlgeschlagen',
  CANCELLED: 'Abgebrochen',
};
const ruleLabels: Record<QualityRule['operation'], string> = {
  required: 'Pflichtwert',
  unique: 'Eindeutiger Wert',
  decimal: 'Dezimalzahl',
  date: 'ISO-Datum / Zeitstempel',
  boolean: 'true oder false',
  range: 'Zahlenbereich',
  allowed_values: 'Erlaubte Werte',
};
const stepLabels = {
  trim: 'Äußere Leerzeichen entfernen',
  drop_duplicates: 'Doppelte Zeilen entfernen',
  drop_empty_rows: 'Leere Zeilen entfernen',
  fill_missing: 'Fehlwerte ersetzen',
  lowercase: 'Kleinschreibung',
  uppercase: 'Großschreibung',
};
function writes(session: Session) {
  return session.roles.some((r) => ['ORG_ADMIN', 'ARCHITECTURE_ANALYST'].includes(r));
}
function active(task: TaskSummary) {
  return ['QUEUED', 'RUNNING'].includes(task.status);
}
function numeric(value: string | null) {
  if (value === null) return '—';
  const number = Number(value);
  return Number.isFinite(number)
    ? number.toLocaleString('de-DE', { maximumSignificantDigits: 8 })
    : value;
}
function post(session: Session, body?: unknown) {
  return { method: 'POST', csrf: session.csrf_token, idempotencyKey: crypto.randomUUID(), body };
}

function useTasks(kind: TaskView['kind'], datasetId?: string) {
  const [revision, setRevision] = useState(0);
  const [before, setBefore] = useState('');
  const [selection, setSelection] = useState('');
  const path =
    '/data-tasks?limit=20&kind=' +
    kind +
    (datasetId ? '&dataset_id=' + datasetId : '') +
    (before ? '&before=' + before : '');
  const { data, error } = useLoad<{ items: TaskSummary[]; next_cursor: string | null }>(
    path,
    revision,
    true,
  );
  const summary = selection ? data?.items.find((t) => t.id === selection) : data?.items[0];
  const detailId = selection || summary?.id;
  const { data: task, error: detailError } = useLoad<TaskView>(
    detailId ? '/data-tasks/' + detailId : null,
    revision,
    true,
  );
  const processing = data?.items.some(active) || (task && active(task));
  useEffect(() => {
    if (!processing) return;
    const timer = window.setTimeout(() => setRevision((r) => r + 1), 1800);
    return () => window.clearTimeout(timer);
  }, [processing, revision]);
  function reload(created?: TaskView) {
    if (created) {
      setBefore('');
      setSelection(created.id);
    }
    setRevision((r) => r + 1);
  }
  const history = (
    <>
      <ErrorNotice error={error} retry={() => reload()} />
      <ErrorNotice error={detailError} retry={() => reload()} />
      {!!data?.items.length && (
        <Field label="Gespeicherter Auftrag">
          <select value={summary?.id ?? ''} onChange={(e) => setSelection(e.target.value)}>
            {data.items.map((t) => (
              <option key={t.id} value={t.id}>
                {date(t.created_at)} · {t.version_no ? 'V' + t.version_no + ' · ' : ''}
                {labels[t.status]} · {t.id.slice(0, 8)}
              </option>
            ))}
          </select>
        </Field>
      )}
      <div className="actions">
        {data?.next_cursor && (
          <button
            className="text-button"
            onClick={() => {
              setBefore(data.next_cursor!);
              setSelection('');
            }}
          >
            Ältere Aufträge
          </button>
        )}
        {before && (
          <button
            className="text-button"
            onClick={() => {
              setBefore('');
              setSelection('');
            }}
          >
            Neueste Aufträge
          </button>
        )}
      </div>
    </>
  );
  return { task, history, reload };
}

function TaskStatus({
  task,
  session,
  reload,
}: {
  task?: TaskView;
  session: Session;
  reload: (task?: TaskView) => void;
}) {
  const [error, setError] = useState<unknown>();
  const [pending, setPending] = useState(false);
  if (!task) return null;
  async function action(name: string) {
    setPending(true);
    setError(undefined);
    try {
      reload(await request<TaskView>('/data-tasks/' + task!.id + '/' + name, post(session)));
    } catch (e) {
      setError(e);
    } finally {
      setPending(false);
    }
  }
  return (
    <div className="task-status">
      <p role="status">
        <strong>{labels[task.status]}</strong> · {task.message}
      </p>
      {active(task) && (
        <progress max={100} value={task.progress} aria-label="Auftragsfortschritt" />
      )}
      {task.error && (
        <p className="notice error" role="alert">
          {task.error}
        </p>
      )}
      <ErrorNotice error={error} />
      {writes(session) && active(task) && (
        <button className="secondary" disabled={pending} onClick={() => void action('cancel')}>
          Auftrag abbrechen
        </button>
      )}
      {writes(session) && ['FAILED', 'CANCELLED'].includes(task.status) && task.kind !== 'PLAN' && (
        <button className="secondary" disabled={pending} onClick={() => void action('retry')}>
          Auftrag erneut starten
        </button>
      )}
    </div>
  );
}

export function SourceImport({
  session,
  navigate,
}: {
  session: Session;
  navigate: (path: string) => void;
}) {
  const [revision, setRevision] = useState(0);
  const { data: catalog, error: catalogError } = useLoad<SourceCatalog>('/data-sources', revision);
  const tasks = useTasks('SOURCE');
  const [sourceId, setSourceId] = useState('');
  const source = catalog?.items.find((s) => s.id === sourceId) ?? catalog?.items[0];
  const [table, setTable] = useState('');
  const selectedTable = source?.tables.includes(table) ? table : (source?.tables[0] ?? '');
  const [name, setName] = useState('');
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<unknown>();
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!source) return;
    setPending(true);
    setError(undefined);
    try {
      tasks.reload(
        await request<TaskView>(
          '/data-sources/import',
          post(session, { source_id: source.id, table: selectedTable, name }),
        ),
      );
    } catch (e) {
      setError(e);
    } finally {
      setPending(false);
    }
  }
  const result = pending ? undefined : tasks.task?.result;
  return (
    <details className="form-card import-disclosure">
      <summary>
        <strong>Datenbankquelle importieren</strong>
        <span>PostgreSQL · konsistenter Snapshot</span>
      </summary>
      <p>
        Eine freigegebene Tabelle wird lesend als unveränderlicher Snapshot übernommen und
        anschließend profiliert. Bis 1 GiB; Zugang und Tabellenfreigabe verwaltet die
        Administration.
      </p>
      <ErrorNotice error={catalogError} retry={() => setRevision((r) => r + 1)} />
      {catalog && !catalog.items.length && (
        <p className="notice info">
          Für diese Organisation ist noch keine PostgreSQL-Quelle registriert.
        </p>
      )}
      {!!catalog?.items.length && writes(session) && (
        <form onSubmit={(e) => void submit(e)}>
          <div className="data-fields">
            <Field label="Datenbankquelle">
              <select
                disabled={pending}
                value={source?.id ?? ''}
                onChange={(e) => {
                  setSourceId(e.target.value);
                  setTable('');
                }}
              >
                {catalog.items.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Quelltabelle">
              <select
                disabled={pending}
                value={selectedTable}
                onChange={(e) => setTable(e.target.value)}
              >
                {source?.tables.map((t) => (
                  <option key={t}>{t}</option>
                ))}
              </select>
            </Field>
            <Field label="Name des Datenbanksnapshots">
              <input
                required
                maxLength={160}
                value={name}
                disabled={pending}
                onChange={(e) => setName(e.target.value)}
              />
            </Field>
          </div>
          <ErrorNotice error={error} />
          <button disabled={pending || !source}>
            {pending ? 'Import wird vorgemerkt …' : 'Datenbanksnapshot importieren'}
          </button>
        </form>
      )}
      {tasks.history}
      <TaskStatus task={tasks.task} session={session} reload={tasks.reload} />
      {result && 'job_id' in result && (
        <div className="notice info">
          <p>Snapshot gespeichert. Die normale Importverarbeitung erstellt das Datenprofil.</p>
          <button className="secondary" onClick={() => navigate('/daten/' + result.dataset_id)}>
            Importierten Datensatz öffnen
          </button>
        </div>
      )}
    </details>
  );
}

function Table({
  caption,
  headers,
  rows,
}: {
  caption: string;
  headers: string[];
  rows: ReactNode[][];
}) {
  return (
    <div className="table-scroll" tabIndex={0} role="region" aria-label={caption}>
      <table>
        <caption>{caption}</caption>
        <thead>
          <tr>
            {headers.map((h) => (
              <th key={h} scope="col">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i}>
              {row.map((cell, j) => (
                <td key={j}>{cell}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {!rows.length && <p className="form-hint">Keine passenden Ergebnisse vorhanden.</p>}
    </div>
  );
}

function AnalysisReport({ result, task }: { result: AnalysisResult; task: TaskView }) {
  const [error, setError] = useState<unknown>();
  const [pending, setPending] = useState(false);
  async function download(format: string) {
    setPending(true);
    setError(undefined);
    try {
      const response = await fetch('/api/v1/data-tasks/' + task.id + '/report?format=' + format, {
        credentials: 'same-origin',
      });
      if (!response.ok)
        throw new Error(
          'Der Bericht konnte nicht geladen werden. Sitzung und Auftragsstatus prüfen.',
        );
      const url = URL.createObjectURL(await response.blob());
      const link = document.createElement('a');
      link.href = url;
      link.download = 'analyse-' + task.id + '.' + format;
      document.body.append(link);
      link.click();
      link.remove();
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (e) {
      setError(e);
    } finally {
      setPending(false);
    }
  }
  return (
    <section className="analysis-report">
      <div className="section-heading">
        <h3>Analysebericht · Version {result.version_no}</h3>
        <span className="version-tag">Qualität {numeric(result.score)} / 100</span>
      </div>
      <p className="form-hint">
        {result.profile.rows.toLocaleString('de-DE')} Zeilen vollständig geprüft ·{' '}
        {date(task.finished_at ?? task.created_at)} · Zahlen in der Ansicht gerundet; Bericht
        enthält Dezimalergebnisse.
      </p>
      <p>{result.score_method}</p>
      <Suspense fallback={<Loading />}>
        <AnalysisCharts key={task.id} result={result} />
      </Suspense>
      <div className="actions">
        <button className="secondary" disabled={pending} onClick={() => void download('html')}>
          Analysebericht herunterladen
        </button>
        <button className="secondary" disabled={pending} onClick={() => void download('json')}>
          Analyse als JSON
        </button>
      </div>
      <ErrorNotice error={error} />
      <Table
        caption="Verteilungen und Ausreißer"
        headers={[
          'Spalte',
          'Gültig',
          'Fehlend',
          'Ungültig',
          'Minimum',
          'Q1',
          'Median',
          'Q3',
          'Maximum',
          'Mittelwert',
          'Standardabweichung',
          'Ausreißer (IQR)',
        ]}
        rows={result.numeric.map((n) => [
          n.column,
          n.count,
          n.missing,
          n.invalid,
          numeric(n.minimum),
          numeric(n.q1),
          numeric(n.median),
          numeric(n.q3),
          numeric(n.maximum),
          numeric(n.mean),
          numeric(n.sample_stddev),
          n.outliers,
        ])}
      />
      <Table
        caption="Korrelationen · paarweise gültige Werte"
        headers={['Spalte X', 'Spalte Y', 'Wertepaare', 'Pearson r']}
        rows={result.correlations.map((c) => [c.x, c.y, c.pairs, numeric(c.pearson)])}
      />
      {result.ruleset && (
        <p>
          Regelsatz: <strong>{result.ruleset.name}</strong> · {date(result.ruleset.created_at)}
        </p>
      )}
      <Table
        caption="Fachliche Qualitätsregeln"
        headers={['Spalte', 'Regel', 'Geprüft', 'Verletzt', 'Beispielzeilen (ab 1)']}
        rows={result.rules.map((r) => [
          r.rule.column,
          ruleLabels[r.rule.operation] +
            (r.rule.operation === 'range'
              ? ' ' + (r.rule.minimum ?? '−∞') + ' … ' + (r.rule.maximum ?? '∞')
              : r.rule.operation === 'allowed_values'
                ? ': ' + r.rule.values.join(', ')
                : ''),
          r.checked,
          r.failed,
          r.example_rows.join(', ') || '—',
        ])}
      />
      {result.time_series.column && (
        <>
          <h3>Zeitverlauf · {result.time_series.column}</h3>
          <p>
            Ungültige Zeitwerte: {result.time_series.invalid_dates} · Fehlende Zeitwerte:{' '}
            {result.time_series.missing_dates} · Ungültige/fehlende Kennzahlen:{' '}
            {result.time_series.invalid_or_missing_metrics}
          </p>
          <Table
            caption={
              'Zeitperioden · ' +
              result.time_series.periods.length +
              ' von ' +
              result.time_series.total_periods
            }
            headers={['Periode (UTC)', 'Zeilen', 'Gültige Kennzahlen', 'Summe', 'Mittelwert']}
            rows={result.time_series.periods.map((p) => [
              p.period,
              p.rows,
              p.valid_values,
              numeric(p.sum),
              numeric(p.mean),
            ])}
          />
        </>
      )}
      <details>
        <summary>Methodik, Grenzen und Prüfsummen</summary>
        <ul>
          {result.notes.map((n) => (
            <li key={n}>{n}</li>
          ))}
        </ul>
        <p className="data-hash">Quelle: {result.content_hash}</p>
        <p className="data-hash">Bericht: {task.result_hash}</p>
      </details>
    </section>
  );
}

export function AnalysisPanel({
  session,
  id,
  version,
}: {
  session: Session;
  id: string;
  version: VersionView;
}) {
  const tasks = useTasks('ANALYSIS', id);
  const [revision, setRevision] = useState(0);
  const { data: saved, error: savedError } = useLoad<{ items: RuleSetView[] }>(
    '/data-rule-sets',
    revision,
  );
  const [rulesetId, setRulesetId] = useState('');
  const [baseRulesetId, setBaseRulesetId] = useState('');
  const [ruleName, setRuleName] = useState('');
  const [rules, setRules] = useState<QualityRule[]>([]);
  const [column, setColumn] = useState(version.profile.columns[0]?.name ?? '');
  const [operation, setOperation] = useState<QualityRule['operation']>('required');
  const [minimum, setMinimum] = useState('');
  const [maximum, setMaximum] = useState('');
  const [values, setValues] = useState('');
  const [numericColumns, setNumericColumns] = useState<string[]>([]);
  const [dateColumn, setDateColumn] = useState('');
  const [metric, setMetric] = useState('');
  const [grain, setGrain] = useState('month');
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<unknown>();
  const columns = version.profile.columns.map((c) => c.name);
  async function saveRules() {
    setPending(true);
    setError(undefined);
    try {
      const created = await request<RuleSetView>(
        '/data-rule-sets',
        post(session, { name: ruleName, rules, replaces_id: baseRulesetId || null }),
      );
      setRulesetId(created.id);
      setBaseRulesetId(created.id);
      setRevision((r) => r + 1);
    } catch (e) {
      setError(e);
    } finally {
      setPending(false);
    }
  }
  async function analyze(event: FormEvent) {
    event.preventDefault();
    setPending(true);
    setError(undefined);
    try {
      tasks.reload(
        await request<TaskView>(
          '/datasets/' + id + '/analyses',
          post(session, {
            version_no: version.version_no,
            numeric_columns: numericColumns,
            date_column: dateColumn || null,
            time_metric: dateColumn && metric ? metric : null,
            time_grain: grain,
            ruleset_id: rulesetId || null,
            rules: rulesetId ? [] : rules,
          }),
        ),
      );
    } catch (e) {
      setError(e);
    } finally {
      setPending(false);
    }
  }
  const result = tasks.task?.result;
  return (
    <section id="dataset-quality" className="form-card" tabIndex={-1}>
      <div className="section-heading">
        <h2>Qualität & Statistik</h2>
        <span className="muted">Vollanalyse · reproduzierbarer Bericht</span>
      </div>
      <p>
        Verteilungen, Ausreißer, Korrelationen und fachliche Regeln für Version {version.version_no}
        . Eine Analyse verändert keine Daten.
      </p>
      {writes(session) && (
        <details>
          <summary>Analyse konfigurieren</summary>
          <form onSubmit={(e) => void analyze(e)}>
            <div className="data-fields">
              <Field
                label="Numerische Analysespalten"
                hint="Bis acht Spalten. Ohne Auswahl: erste acht numerisch erkannte Spalten. Mehrfachauswahl mit Strg/Cmd."
              >
                <select
                  multiple
                  size={Math.min(6, columns.length)}
                  value={numericColumns}
                  disabled={pending}
                  onChange={(e) =>
                    setNumericColumns(Array.from(e.target.selectedOptions, (o) => o.value))
                  }
                >
                  {columns.map((c) => (
                    <option key={c}>{c}</option>
                  ))}
                </select>
              </Field>
              <Field label="Zeitspalte">
                <select
                  value={dateColumn}
                  disabled={pending}
                  onChange={(e) => setDateColumn(e.target.value)}
                >
                  <option value="">Keine Zeitreihe</option>
                  {columns.map((c) => (
                    <option key={c}>{c}</option>
                  ))}
                </select>
              </Field>
              {dateColumn && (
                <>
                  <Field label="Zeitreihen-Kennzahl">
                    <select
                      value={metric}
                      disabled={pending}
                      onChange={(e) => setMetric(e.target.value)}
                    >
                      <option value="">Nur Zeilen zählen</option>
                      {columns.map((c) => (
                        <option key={c}>{c}</option>
                      ))}
                    </select>
                  </Field>
                  <Field label="Zeitintervall">
                    <select
                      value={grain}
                      disabled={pending}
                      onChange={(e) => setGrain(e.target.value)}
                    >
                      <option value="month">Monat</option>
                      <option value="day">Tag</option>
                    </select>
                  </Field>
                </>
              )}
            </div>
            <fieldset disabled={pending}>
              <legend>Wiederverwendbare Qualitätsregeln</legend>
              <ErrorNotice error={savedError} retry={() => setRevision((r) => r + 1)} />
              <Field label="Qualitätsregelsatz">
                <select
                  value={rulesetId}
                  onChange={(e) => {
                    const selected = saved?.items.find((r) => r.id === e.target.value);
                    setRulesetId(e.target.value);
                    setBaseRulesetId(e.target.value);
                    setRules(selected?.rules ?? []);
                    setRuleName(selected?.name ?? '');
                  }}
                >
                  <option value="">Eigene Regeln / ohne Regelsatz</option>
                  {saved?.items.map((r) => (
                    <option key={r.id} value={r.id}>
                      {r.name} · {date(r.created_at)} · {r.id.slice(0, 8)}
                    </option>
                  ))}
                </select>
              </Field>
              <ol className="data-steps">
                {rules.map((r, i) => (
                  <li key={i}>
                    <span>
                      {r.column} · {ruleLabels[r.operation]}
                      {r.operation === 'range'
                        ? ': ' + (r.minimum ?? '−∞') + ' … ' + (r.maximum ?? '∞')
                        : r.operation === 'allowed_values'
                          ? ': ' + r.values.join(', ')
                          : ''}
                    </span>
                    <button
                      type="button"
                      className="text-button"
                      onClick={() => {
                        setRules(rules.filter((_, n) => n !== i));
                        setRulesetId('');
                      }}
                      aria-label={'Regel ' + (i + 1) + ' entfernen'}
                    >
                      Entfernen
                    </button>
                  </li>
                ))}
              </ol>
              <div className="data-fields">
                <Field label="Regelspalte">
                  <select value={column} onChange={(e) => setColumn(e.target.value)}>
                    {columns.map((c) => (
                      <option key={c}>{c}</option>
                    ))}
                  </select>
                </Field>
                <Field label="Qualitätsregel">
                  <select
                    value={operation}
                    onChange={(e) => setOperation(e.target.value as QualityRule['operation'])}
                  >
                    {Object.entries(ruleLabels).map(([key, label]) => (
                      <option key={key} value={key}>
                        {label}
                      </option>
                    ))}
                  </select>
                </Field>
                {operation === 'range' && (
                  <>
                    <Field label="Untergrenze" hint="Dezimalpunkt; mindestens eine Grenze angeben.">
                      <input
                        maxLength={100}
                        value={minimum}
                        onChange={(e) => setMinimum(e.target.value)}
                      />
                    </Field>
                    <Field label="Obergrenze">
                      <input
                        maxLength={100}
                        value={maximum}
                        onChange={(e) => setMaximum(e.target.value)}
                      />
                    </Field>
                  </>
                )}
                {operation === 'allowed_values' && (
                  <Field
                    label="Erlaubte Werte"
                    hint="Ein Originalwert pro Zeile; maximal 100 Werte."
                  >
                    <textarea
                      value={values}
                      onChange={(e) => setValues(e.target.value)}
                      maxLength={51300}
                    />
                  </Field>
                )}
              </div>
              <button
                type="button"
                className="secondary"
                disabled={
                  rules.length >= 50 ||
                  (operation === 'range' && !minimum && !maximum) ||
                  (operation === 'allowed_values' && !values)
                }
                onClick={() => {
                  setRules([
                    ...rules,
                    {
                      column,
                      operation,
                      minimum: operation === 'range' && minimum ? minimum : null,
                      maximum: operation === 'range' && maximum ? maximum : null,
                      values: operation === 'allowed_values' ? values.split('\n') : [],
                    },
                  ]);
                  setRulesetId('');
                }}
              >
                Qualitätsregel hinzufügen
              </button>
              <Field label="Name des Regelsatzes">
                <input
                  value={ruleName}
                  maxLength={160}
                  onChange={(e) => setRuleName(e.target.value)}
                />
              </Field>
              <button
                type="button"
                className="secondary"
                disabled={!rules.length || !ruleName.trim()}
                onClick={() => void saveRules()}
              >
                Regelsatz als neue Version speichern
              </button>
              <p className="form-hint">
                Gespeicherte Regeln und Analyseergebnisse bleiben unveränderlich. Änderungen werden
                als neue Regelsatzversion gespeichert.
              </p>
            </fieldset>
            <ErrorNotice error={error} />
            {numericColumns.length > 8 && (
              <p role="alert">Bitte höchstens acht numerische Spalten auswählen.</p>
            )}
            <button disabled={pending || numericColumns.length > 8}>
              {pending ? 'Analyse wird vorgemerkt …' : 'Vollanalyse starten'}
            </button>
          </form>
        </details>
      )}
      {tasks.history}
      <TaskStatus task={tasks.task} session={session} reload={tasks.reload} />
      {!tasks.task && (
        <p className="form-hint">
          Noch kein gespeicherter Analysebericht. Das Basisprofil und die Visualisierungen sind
          bereits oben verfügbar.
        </p>
      )}
      {result && 'numeric' in result && tasks.task && (
        <AnalysisReport result={result} task={tasks.task} />
      )}
    </section>
  );
}

export function PlanPanel({
  session,
  id,
  version,
  onPreview,
}: {
  session: Session;
  id: string;
  version: VersionView;
  onPreview: (job: JobView) => void;
}) {
  const tasks = useTasks('PLAN', id);
  const { data: catalog, error: catalogError } = useLoad<SourceCatalog>('/data-sources');
  const [mode, setMode] = useState('rules');
  const [consent, setConsent] = useState(false);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<unknown>();
  async function plan() {
    setPending(true);
    setError(undefined);
    try {
      tasks.reload(
        await request<TaskView>(
          '/datasets/' + id + '/plans',
          post(session, {
            version_no: version.version_no,
            mode,
            approve_external_processing: consent,
          }),
        ),
      );
    } catch (e) {
      setError(e);
    } finally {
      setPending(false);
    }
  }
  async function preview() {
    if (!tasks.task) return;
    setPending(true);
    setError(undefined);
    try {
      onPreview(await request<JobView>('/data-tasks/' + tasks.task.id + '/preview', post(session)));
    } catch (e) {
      setError(e);
    } finally {
      setPending(false);
    }
  }
  const result: PlanResult | undefined =
    tasks.task?.result && 'steps' in tasks.task.result ? tasks.task.result : undefined;
  return (
    <details className="form-card">
      <summary>
        <strong>Assistierte Bereinigungsplanung</strong>
        <span>Geprüfte Vorschläge · menschliche Entscheidung</span>
      </summary>
      <p>
        Aus Profilbefunden entstehen begrenzte Änderungskandidaten. Verifier und Freigaberegeln
        prüfen jeden Plan. Eine Übernahme erfolgt erst nach berechneter Vorschau und ausdrücklicher
        Bestätigung.
      </p>
      <ErrorNotice error={catalogError} />
      <Field label="Planungsverfahren">
        <select
          value={mode}
          disabled={pending}
          onChange={(e) => {
            setMode(e.target.value);
            setConsent(false);
          }}
        >
          <option value="rules">Regelbasierte Vorschläge · keine KI</option>
          {catalog?.live_ai_available && (
            <option value="openai">KI-gestützte Auswahl · OpenAI</option>
          )}
        </select>
      </Field>
      {!catalog?.live_ai_available && (
        <p className="form-hint">
          Live-KI ist für diese Organisation nicht konfiguriert oder nicht freigegeben. Die
          regelbasierte Planung ist verfügbar.
        </p>
      )}
      {mode === 'openai' && (
        <label className="checkbox-field">
          <input
            type="checkbox"
            checked={consent}
            disabled={pending}
            onChange={(e) => setConsent(e.target.checked)}
          />
          Ich stimme der externen Verarbeitung aggregierter Profilzahlen und anonymisierter
          Kandidaten-IDs zu. Keine Zellwerte oder Spaltennamen werden übertragen; das gemeinsame
          KI-Budget gilt.
        </label>
      )}
      <ErrorNotice error={error} />
      <button disabled={pending || (mode === 'openai' && !consent)} onClick={() => void plan()}>
        {pending ? 'Auftrag läuft …' : 'Bereinigungsplan erstellen'}
      </button>
      {pending && <Loading text="Begrenzter Planungsauftrag wird verarbeitet …" />}
      {tasks.history}
      <TaskStatus task={tasks.task} session={session} reload={tasks.reload} />
      {result && (
        <section className="data-preview">
          <h3>
            {result.mode === 'openai'
              ? 'KI-gestützter, geprüfter Plan'
              : 'Regelbasiert erstellter Plan'}
          </h3>
          <p>
            Quellversion {tasks.task?.version_no} · {result.steps.length} Schritte · reserviertes
            Maximalbudget: {numeric(result.reserved_usd)} USD
          </p>
          <ol>
            {result.candidates.map((c) => (
              <li key={c.id}>
                <strong>
                  {stepLabels[c.step.operation]}
                  {c.step.column ? ' · ' + c.step.column : ''}
                </strong>
                <p>{c.reason}</p>
                <small>Evidenz: {c.evidence} · Mittleres Änderungsrisiko</small>
              </li>
            ))}
          </ol>
          {!result.steps.length && (
            <p>
              Keine ausreichend belegte Änderung vorgeschlagen. Die manuelle Bereinigung bleibt
              verfügbar.
            </p>
          )}
          <p>{result.uncertainty}</p>
          <p>{result.required_decision}</p>
          <details>
            <summary>Prüfpfad der Agent-Rollen</summary>
            <ol>
              {result.trace.map((t) => (
                <li key={t.role}>
                  <strong>{t.role}</strong>: {t.decision}
                </li>
              ))}
            </ol>
            <p className="data-hash">Geprüfte Quelle: {result.source_hash}</p>
            <p className="data-hash">Plan: {tasks.task?.result_hash}</p>
          </details>
          {tasks.task?.version_no !== version.version_no && (
            <p className="notice info">
              Dieser Plan gehört zu einer anderen Version. Für den aktuellen Stand neu planen.
            </p>
          )}
          <button
            disabled={
              pending || !result.steps.length || tasks.task?.version_no !== version.version_no
            }
            onClick={() => void preview()}
          >
            Geprüften Plan als Vorschau berechnen
          </button>
        </section>
      )}
    </details>
  );
}
