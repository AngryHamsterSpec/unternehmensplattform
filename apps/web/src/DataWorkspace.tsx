import { lazy, Suspense, useEffect, useRef, useState } from 'react';
import type { FormEvent } from 'react';
import { isAbort, request } from './api';
import { ErrorNotice, Field, Loading, Empty } from './components';
import type { Session, Page } from './types';
import type {
  DatasetSummary,
  DatasetView,
  DataProfile,
  JobView,
  Step,
  VersionView,
  UploadView,
  ImportOptions,
} from './generated/domain';
import { useLoad } from './useLoad';
import { date } from './format';
import { Icon, SectionNav, TableToolbar, WorkspaceSummary } from './DesignSystem';
import { AnalysisPanel, PlanPanel, SourceImport } from './DataIntelligence';

const DataCharts = lazy(() => import('./DataCharts'));

const stepLabels: Record<Step['operation'], string> = {
  trim: 'Äußere Leerzeichen entfernen',
  fill_missing: 'Fehlwerte ersetzen',
  lowercase: 'In Kleinbuchstaben umwandeln',
  uppercase: 'In Großbuchstaben umwandeln',
  drop_duplicates: 'Doppelte Zeilen entfernen',
  drop_empty_rows: 'Vollständig leere Zeilen entfernen',
};
const typeLabels = {
  empty: 'Leer',
  decimal: 'Dezimalzahl',
  boolean: 'Wahrheitswert',
  date: 'Datum',
  text: 'Text',
};
const jobLabels = {
  QUEUED: 'Wartet auf Verarbeitung',
  RUNNING: 'Wird verarbeitet',
  CANCELLED: 'Abgebrochen',
  SUCCEEDED: 'Berechnung abgeschlossen',
  FAILED: 'Verarbeitung fehlgeschlagen',
};
export const DEMO_CSV =
  'Name;Abteilung;Betrag;Datum\n Anna ;Vertrieb;120.50;2026-09-01\nAnna;Vertrieb;120.50;2026-09-01\nBen;;80;2026-09-02\nClara;IT;400;2026-09-03\n; ; ;\n';

const CHART_DEMO_CSV =
  'Team;Umsatz_EUR;Kosten_EUR;Kunden\n' +
  Array.from({ length: 180 }, (_, i) => {
    const teams = ['Nord', 'Süd', 'West', 'Ost'];
    const revenue = 18000 + i * 165 + ((i * 7919) % 9000);
    return [
      teams[i % 4],
      revenue,
      Math.round(revenue * (0.52 + (i % 9) / 100)),
      80 + ((i * 13) % 160),
    ].join(';');
  }).join('\n') +
  '\n';

function statistic(value: string | null) {
  return value === null ? '—' : value.replace(/(\.\d*?[1-9])0+$|\.0+$/, '$1').replace('.', ',');
}

function canWrite(session: Session) {
  return session.roles.some((role) => role === 'ORG_ADMIN' || role === 'ARCHITECTURE_ANALYST');
}

export function DataWorkspace({
  session,
  id,
  navigate,
}: {
  session: Session;
  id?: string;
  navigate: (path: string) => void;
}) {
  return id ? (
    <DatasetDetail key={id} session={session} id={id} />
  ) : (
    <DatasetList session={session} navigate={navigate} />
  );
}

function DatasetList({
  session,
  navigate,
}: {
  session: Session;
  navigate: (path: string) => void;
}) {
  const { data, error } = useLoad<Page<DatasetSummary>>('/datasets');
  const [extra, setExtra] = useState<DatasetSummary[]>([]);
  const [cursor, setCursor] = useState<string | null>();
  const [query, setQuery] = useState('');
  const [pending, setPending] = useState(false);
  const [loadError, setLoadError] = useState<unknown>();
  const importPanel = useRef<HTMLDetailsElement>(null);
  const [statusFilter, setStatusFilter] = useState('all');
  const all = [...(data?.items ?? []), ...extra];
  const shown = all.filter(
    (item) =>
      (statusFilter === 'all' ||
        (statusFilter === 'versioned' ? !!item.current_version : !item.current_version)) &&
      (item.name + ' ' + item.filename)
        .toLocaleLowerCase('de')
        .includes(query.toLocaleLowerCase('de')),
  );
  const next = cursor === undefined ? data?.next_cursor : cursor;
  async function more() {
    if (!next) return;
    setPending(true);
    try {
      const page = await request<Page<DatasetSummary>>(
        '/datasets?cursor=' + encodeURIComponent(next),
      );
      setExtra((items) => [...items, ...page.items]);
      setCursor(page.next_cursor);
      setLoadError(undefined);
    } catch (e) {
      setLoadError(e);
    } finally {
      setPending(false);
    }
  }

  return (
    <section>
      <header className="page-header">
        <div>
          <p className="eyebrow">Datenbestand & Qualität</p>
          <h1>Datenwerkstatt</h1>
          <p>Originale bewahren. Qualität verstehen. Änderungen bewusst übernehmen.</p>
        </div>
        {canWrite(session) && (
          <button
            onClick={() => {
              if (importPanel.current) {
                importPanel.current.open = true;
                importPanel.current.querySelector('input')?.focus();
              }
            }}
          >
            <Icon name="upload" /> Datei importieren
          </button>
        )}
      </header>
      <WorkspaceSummary
        items={[
          { label: 'Datensätze', value: data ? all.length : '—', hint: 'Im geladenen Bestand' },
          {
            label: 'Versioniert',
            value: data ? all.filter((item) => item.current_version).length : '—',
            hint: 'Zur Analyse verfügbar',
          },
          {
            label: 'Ohne Datenversion',
            value: data ? all.filter((item) => !item.current_version).length : '—',
            hint: 'Auftragsstatus im Datensatz',
          },
        ]}
      />
      {canWrite(session) && (
        <details className="form-card import-disclosure" ref={importPanel}>
          <summary>
            <Icon name="upload" />
            <strong>Daten hinzufügen</strong>
            <span>CSV · Excel · JSON · Parquet</span>
            <span className="import-limit">Bis 1 GiB</span>
          </summary>
          <ImportForm
            session={session}
            onImported={(job) => navigate('/daten/' + job.dataset_id)}
          />
        </details>
      )}
      <SourceImport session={session} navigate={navigate} />
      <ErrorNotice error={error ?? loadError} />
      <section className="form-card catalog-panel">
        <div className="section-heading">
          <h2>Gespeicherte Datensätze</h2>
          <span className="muted">Originale & Ableitungen</span>
        </div>
        <TableToolbar
          label="Geladene Datensätze filtern"
          query={query}
          onQuery={setQuery}
          count={shown.length}
          total={all.length}
        >
          <label className="table-select">
            Datenstand
            <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
              <option value="all">Alle Datenstände</option>
              <option value="versioned">Versioniert</option>
              <option value="pending">Ohne Datenversion</option>
            </select>
          </label>
        </TableToolbar>
        {!data && !error ? (
          <Loading />
        ) : !all.length ? (
          <Empty title="Noch keine Datensätze">
            <p>Beginne mit einer synthetischen Beispieldatei.</p>
          </Empty>
        ) : (
          <div className="table-scroll">
            <table className="catalog-table">
              <caption className="sr-only">Gespeicherte Datensätze im geladenen Bestand</caption>
              <thead>
                <tr>
                  <th>Datensatz</th>
                  <th>Originaldatei</th>
                  <th>Stand</th>
                  <th>Erstellt</th>
                  <th>Aktion</th>
                </tr>
              </thead>
              <tbody>
                {shown.map((item) => (
                  <tr key={item.id}>
                    <th scope="row">
                      <span className="record-name">
                        <Icon name="file" />
                        {item.name}
                      </span>
                    </th>
                    <td>
                      <span className="file-type">
                        {item.filename.split('.').at(-1)?.toUpperCase()}
                      </span>
                      <span className="file-name">{item.filename}</span>
                    </td>
                    <td>
                      <span
                        className={item.current_version ? 'version-tag' : 'badge badge-unknown'}
                      >
                        {item.current_version
                          ? 'Version ' + item.current_version
                          : 'Ohne Datenversion'}
                      </span>
                    </td>
                    <td>{date(item.created_at)}</td>
                    <td>
                      <button className="text-button" onClick={() => navigate('/daten/' + item.id)}>
                        Datensatz öffnen →
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {shown.length === 0 && (
              <p className="table-no-results">Keine geladenen Datensätze passen zum Filter.</p>
            )}
          </div>
        )}
        {next && (
          <div className="data-pagination">
            <button className="secondary" disabled={pending} onClick={() => void more()}>
              {pending ? 'Wird geladen …' : 'Weitere Datensätze laden'}
            </button>
          </div>
        )}
      </section>
    </section>
  );
}

export function ImportForm({
  session,
  onImported,
}: {
  session: Session;
  onImported: (job: JobView) => void;
}) {
  const [name, setName] = useState('');
  const [file, setFile] = useState<File>();
  const [delimiter, setDelimiter] = useState('auto');
  const [encoding, setEncoding] = useState('auto');
  const [hasHeader, setHasHeader] = useState(true);
  const [worksheet, setWorksheet] = useState(1);
  const [tableName, setTableName] = useState('');
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<unknown>();
  const [upload, setUpload] = useState<UploadView>();
  const [progress, setProgress] = useState(0);
  const [message, setMessage] = useState('');
  const controller = useRef<AbortController | null>(null);
  const uploadKey = 'csv-upload:' + session.organization?.id;
  const [uploadRevision, setUploadRevision] = useState(0);
  const isJson = /\.(json|jsonl)$/i.test(file?.name ?? upload?.filename ?? '');
  const isParquet = /\.parquet$/i.test(file?.name ?? upload?.filename ?? '');
  const isXlsx = /\.xlsx$/i.test(file?.name ?? upload?.filename ?? '');
  const isSqlite = /\.(sqlite|sqlite3|db)$/i.test(file?.name ?? upload?.filename ?? '');
  const { data: openUploads } = useLoad<Page<UploadView>>('/data-uploads', uploadRevision);

  useEffect(() => () => controller.current?.abort(), []);
  async function submit(event: FormEvent) {
    event.preventDefault();
    setError(undefined);
    if (!file || !file.size || file.size > 1073741824) {
      setError(
        new Error(
          'Bitte eine CSV-, XLSX-, JSON-, Parquet- oder SQLite-Datei zwischen 1 Byte und 1 GiB auswählen (1.073.741.824 Bytes).',
        ),
      );
      return;
    }
    if (upload && (file.size !== upload.expected_bytes || file.name !== upload.filename)) {
      setError(
        new Error(
          'Bitte die ursprüngliche Datei mit unverändertem Namen und gleicher Größe auswählen.',
        ),
      );
      return;
    }
    setPending(true);
    controller.current = new AbortController();
    const signal = controller.current.signal;
    try {
      const fingerprint = JSON.stringify([
        file.name,
        file.size,
        file.lastModified,
        name,
        delimiter,
        encoding,
        hasHeader,
        worksheet,
        isSqlite ? tableName : null,
      ]);
      let current = upload;
      const stored = localStorage.getItem(uploadKey);
      if (!current && stored) {
        const saved = JSON.parse(stored) as { id: string; fingerprint: string };
        if (saved.fingerprint === fingerprint) {
          current = await request<UploadView>('/data-uploads/' + saved.id, { signal });
          if (current.status === 'CANCELLED') current = undefined;
        }
      }
      if (!current) {
        current = await request<UploadView>('/data-uploads', {
          method: 'POST',
          csrf: session.csrf_token,
          signal,
          body: {
            name,
            filename: file.name,
            total_bytes: file.size,
            delimiter,
            encoding,
            has_header: hasHeader,
            worksheet,
            table_name: isSqlite && tableName ? tableName : null,
          },
        });
        localStorage.setItem(uploadKey, JSON.stringify({ id: current.id, fingerprint }));
      }
      setUpload(current);
      if (current.status !== 'SEALED') {
        // Wiederholte Abschnitte werden serverseitig mit ihrem Hash verglichen.
        // So kann eine andere lokale Datei niemals unbemerkt angehängt werden.
        for (
          let ordinal = 0, offset = 0;
          offset < file.size;
          ordinal++, offset += current.chunk_bytes
        ) {
          setMessage('Datei wird in Abschnitten übertragen und geprüft …');
          current = await request<UploadView>(
            '/data-uploads/' + current.id + '/chunks/' + ordinal,
            {
              method: 'PUT',
              csrf: session.csrf_token,
              signal,
              rawBody: file.slice(offset, offset + current.chunk_bytes),
            },
          );
          setUpload(current);
          setProgress(Math.round((100 * current.received_bytes) / file.size));
        }
      }
      setMessage('Upload vollständig. Die Gesamtprüfsumme wird geprüft …');
      const job = await request<JobView>('/data-uploads/' + current.id + '/complete', {
        method: 'POST',
        csrf: session.csrf_token,
        signal,
      });
      localStorage.removeItem(uploadKey);
      setUpload(undefined);
      onImported(job);
    } catch (e) {
      if (isAbort(e)) setMessage('Upload pausiert. Mit derselben Datei fortsetzen.');
      else setError(e);
    } finally {
      setPending(false);
    }
  }
  async function cancelUpload(target = upload) {
    if (!target) return;
    setPending(true);
    try {
      await request('/data-uploads/' + target.id + '/cancel', {
        method: 'POST',
        csrf: session.csrf_token,
      });
      localStorage.removeItem(uploadKey);
      if (upload?.id === target.id) setUpload(undefined);
      setUploadRevision((value) => value + 1);
      setProgress(0);
      setMessage('Upload abgebrochen; temporäre Abschnitte wurden entfernt.');
    } catch (e) {
      setError(e);
    } finally {
      setPending(false);
    }
  }
  return (
    <form className="form-card" onSubmit={(event) => void submit(event)}>
      <div className="section-heading">
        <h2>Datendatei importieren</h2>
        <button
          type="button"
          className="secondary"
          disabled={pending || !!upload}
          onClick={() => {
            setFile(new File([DEMO_CSV], 'synthetische-abteilungen.csv', { type: 'text/csv' }));
            setName('Synthetische Abteilungsdaten');
            setDelimiter('auto');
            setEncoding('auto');
            setHasHeader(true);
            setError(undefined);
          }}
        >
          Synthetische CSV laden
        </button>
      </div>
      <button
        type="button"
        className="text-button"
        disabled={pending || !!upload}
        onClick={() => {
          setFile(
            new File([CHART_DEMO_CSV], 'synthetische-visualisierung.csv', { type: 'text/csv' }),
          );
          setName('Synthetische Vertriebsanalyse');
          setDelimiter('auto');
          setEncoding('auto');
          setHasHeader(true);
          setError(undefined);
        }}
      >
        Diagramm-Beispiel laden · 180 Zeilen
      </button>
      {!upload && !!openUploads?.items.length && (
        <section className="notice info" aria-label="Offene Uploads">
          <h3>Unterbrochene Uploads</h3>
          <p>
            Zum Fortsetzen dieselbe Datei erneut auswählen. Bereits gespeicherte Abschnitte werden
            geprüft.
          </p>
          {openUploads.items.map((item) => (
            <div key={item.id}>
              <p>
                <strong>{item.filename}</strong> · {item.received_bytes.toLocaleString('de-DE')} von{' '}
                {item.expected_bytes.toLocaleString('de-DE')} Bytes
              </p>
              <button
                type="button"
                className="secondary"
                disabled={pending}
                onClick={() => {
                  setUpload(item);
                  setName(item.name);
                  setDelimiter(item.delimiter);
                  setEncoding(item.encoding);
                  setHasHeader(item.has_header);
                  setWorksheet(item.worksheet);
                  setTableName(item.table_name ?? '');
                  setFile(undefined);
                  setProgress(Math.round((100 * item.received_bytes) / item.expected_bytes));
                  setMessage('Bitte dieselbe Datei erneut auswählen.');
                }}
              >
                Diesen Upload fortsetzen
              </button>
              <button
                type="button"
                className="secondary"
                disabled={pending}
                onClick={() => void cancelUpload(item)}
              >
                Diesen Upload abbrechen
              </button>
            </div>
          ))}
        </section>
      )}
      <div className="data-fields">
        <Field label="Datensatzname">
          <input
            required
            maxLength={160}
            value={name}
            disabled={pending || !!upload}
            onChange={(e) => setName(e.target.value)}
          />
        </Field>
        <Field
          label="Datendatei"
          hint="CSV, XLSX, JSON/JSONL, Parquet oder SQLite bis 1 GiB. Upload in Abschnitten von 4 MiB. Je Format gelten zusätzliche Strukturgrenzen."
        >
          <input
            type="file"
            aria-label="Datendatei"
            key={upload?.id ?? 'new'}
            accept=".csv,.xlsx,.json,.jsonl,.parquet,.sqlite,.sqlite3,.db,text/csv,application/json,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            disabled={pending}
            onChange={(e) => setFile(e.target.files?.[0])}
          />
        </Field>
        {!isJson && !isXlsx && !isParquet && !isSqlite && (
          <CsvSettings
            delimiter={delimiter}
            encoding={encoding}
            hasHeader={hasHeader}
            disabled={pending || !!upload}
            setDelimiter={setDelimiter}
            setEncoding={setEncoding}
            setHasHeader={setHasHeader}
          />
        )}
        {isXlsx && (
          <XlsxSettings
            worksheet={worksheet}
            setWorksheet={setWorksheet}
            hasHeader={hasHeader}
            setHasHeader={setHasHeader}
            disabled={pending || !!upload}
          />
        )}
        {isSqlite && (
          <SqliteSettings
            tableName={tableName}
            setTableName={setTableName}
            disabled={pending || !!upload}
          />
        )}
        {isParquet && (
          <p className="form-hint">
            Parquet: eine Datei mit flachen Spalten. Spaltennamen kommen aus dem Schema; null wird
            leer. Keine binären oder verschachtelten Werte. Bis 64 MiB entpackt je Zeilengruppe, 8
            MiB Metadaten und 4.096 Zeilengruppen. Größere Gruppen bitte vorab aufteilen.
          </p>
        )}
        {isJson && (
          <p className="notice info">
            JSON: Array flacher Objekte oder ein Objekt je JSONL-Zeile. Fehlende Schlüssel und null
            werden zu leeren Zellen. Verschachtelte Werte benötigen eine vorherige Aufbereitung; die
            Originaldatei bleibt erhalten.
          </p>
        )}
      </div>
      {file && (
        <p>
          Ausgewählt: <strong>{file.name}</strong> · {file.size.toLocaleString('de-DE')} Bytes
        </p>
      )}
      <p className="form-hint">
        Bis 256 Spalten und 1.048.576 Zeichen je Zelle. CSV und JSON haben keine feste
        Zeilenanzahlgrenze. Zahlen werden mit Dezimalpunkt erkannt. Originalwerte bleiben erhalten.
      </p>
      {(pending || upload || message) && (
        <div className="notice info" role="status">
          <strong>Upload: {progress} %</strong>
          <progress aria-label="Upload-Fortschritt" max={100} value={progress} />
          <p>{message}</p>
        </div>
      )}
      <ErrorNotice error={error} />
      <button disabled={pending || !file}>
        {pending
          ? 'Import läuft …'
          : upload
            ? 'Upload fortsetzen'
            : isSqlite
              ? 'SQLite importieren'
              : isJson
                ? 'JSON importieren'
                : isParquet
                  ? 'Parquet importieren'
                  : isXlsx
                    ? 'Excel importieren'
                    : 'CSV importieren'}
      </button>
      {pending && (
        <button className="secondary" type="button" onClick={() => controller.current?.abort()}>
          Upload pausieren
        </button>
      )}
      {upload && !pending && (
        <button className="secondary" type="button" onClick={() => void cancelUpload()}>
          Upload abbrechen
        </button>
      )}
    </form>
  );
}

function XlsxSettings({
  worksheet,
  setWorksheet,
  hasHeader,
  setHasHeader,
  disabled,
}: {
  worksheet: number;
  setWorksheet: (value: number) => void;
  hasHeader: boolean;
  setHasHeader: (value: boolean) => void;
  disabled: boolean;
}) {
  return (
    <>
      <Field
        label="Arbeitsblatt (Nummer)"
        hint="Reihenfolge in der Excel-Datei, beginnend bei 1. Ein sichtbares Blatt auswählen."
      >
        <input
          type="number"
          min={1}
          max={100}
          required
          value={worksheet}
          disabled={disabled}
          onChange={(e) => setWorksheet(Number(e.target.value))}
        />
      </Field>
      <label className="check-field">
        <input
          type="checkbox"
          checked={hasHeader}
          disabled={disabled}
          onChange={(e) => setHasHeader(e.target.checked)}
        />
        Erste Zeile enthält Spaltennamen
      </label>
      <p className="form-hint">
        XLSX: ein tabellarisches Arbeitsblatt, höchstens 256 Spalten. Formelzellen bitte zuvor als
        Werte speichern. Datumswerte werden ins ISO-Format übertragen; Zahlenformate und führende
        Nullen aus Excel-Formatierungen werden nicht übernommen. Keine Makros oder externen
        Verknüpfungen. Bis 2 GiB entpackt, 4 MiB gemeinsame Texttabelle und 16 MiB Metadaten;
        größere Arbeitsbücher bitte als CSV exportieren.
      </p>
    </>
  );
}

function CsvSettings({
  delimiter,
  encoding,
  hasHeader,
  disabled,
  setDelimiter,
  setEncoding,
  setHasHeader,
}: {
  delimiter: string;
  encoding: string;
  hasHeader: boolean;
  disabled: boolean;
  setDelimiter: (value: string) => void;
  setEncoding: (value: string) => void;
  setHasHeader: (value: boolean) => void;
}) {
  return (
    <>
      <Field label="Trennzeichen" hint="Automatisch erkennt Komma, Semikolon, Tabulator und |.">
        <select
          aria-label="Trennzeichen"
          value={delimiter}
          disabled={disabled}
          onChange={(e) => setDelimiter(e.target.value)}
        >
          <option value="auto">Automatisch erkennen (empfohlen)</option>
          <option value=",">Komma</option>
          <option value=";">Semikolon</option>
          <option value={'\t'}>Tabulator</option>
          <option value="|">Senkrechter Strich |</option>
        </select>
      </Field>
      <Field label="Dateikodierung">
        <select
          aria-label="Dateikodierung"
          value={encoding}
          disabled={disabled}
          onChange={(e) => setEncoding(e.target.value)}
        >
          <option value="auto">Automatisch · UTF-8 / UTF-16 mit BOM</option>
          <option value="utf-8-sig">UTF-8 (mit oder ohne BOM)</option>
          <option value="utf-16">UTF-16 (mit BOM)</option>
          <option value="cp1252">Windows-1252 · ältere Excel-Dateien</option>
        </select>
      </Field>
      <label className="check-field">
        <input
          type="checkbox"
          checked={hasHeader}
          disabled={disabled}
          onChange={(e) => setHasHeader(e.target.checked)}
        />
        Erste Zeile enthält Spaltennamen
      </label>
    </>
  );
}

function SqliteSettings({
  tableName,
  setTableName,
  disabled,
}: {
  tableName: string;
  setTableName: (value: string) => void;
  disabled: boolean;
}) {
  return (
    <>
      <Field
        label="SQLite-Tabelle"
        hint="Optional bei genau einer Datentabelle. Bei mehreren Tabellen den genauen Namen angeben; nach einem Fehler ist die Auswahl ohne erneuten Upload änderbar."
      >
        <input
          value={tableName}
          onChange={(event) => setTableName(event.target.value)}
          maxLength={100}
          disabled={disabled}
        />
      </Field>
      <p className="form-hint">
        Vollständiger, unverschlüsselter SQLite-Snapshot im DELETE-Journalmodus. Eine gewöhnliche
        Tabelle je Import; keine Views, virtuellen oder berechneten Spalten und keine Binärwerte.
        NULL wird leer. Die Originaldatenbank bleibt unverändert.
      </p>
    </>
  );
}

function RetryImport({
  session,
  id,
  filename,
  onQueued,
}: {
  session: Session;
  id: string;
  filename: string;
  onQueued: () => void;
}) {
  const [delimiter, setDelimiter] = useState('auto');
  const [encoding, setEncoding] = useState('auto');
  const [hasHeader, setHasHeader] = useState(true);
  const [worksheet, setWorksheet] = useState(1);
  const [tableName, setTableName] = useState('');
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<unknown>();
  async function retry(event: FormEvent) {
    event.preventDefault();
    setError(undefined);
    setPending(true);
    try {
      const body = {
        delimiter,
        encoding,
        has_header: hasHeader,
        worksheet,
        table_name: /\.(sqlite|sqlite3|db)$/i.test(filename) && tableName ? tableName : null,
      } as ImportOptions;
      await request<JobView>('/datasets/' + id + '/retry-import', {
        method: 'POST',
        csrf: session.csrf_token,
        body,
      });
      onQueued();
    } catch (e) {
      setError(e);
    } finally {
      setPending(false);
    }
  }
  return (
    <form className="form-card" onSubmit={(event) => void retry(event)}>
      <h2>Import aus Originaldatei wiederholen</h2>
      <p>
        Die Datei ist bereits vollständig gespeichert. Passe die Leseeinstellungen an; ein erneuter
        Upload ist nicht nötig.
      </p>
      <div className="data-fields">
        {!/\.(json|jsonl|xlsx|parquet|sqlite|sqlite3|db)$/i.test(filename) && (
          <CsvSettings
            delimiter={delimiter}
            encoding={encoding}
            hasHeader={hasHeader}
            disabled={pending}
            setDelimiter={setDelimiter}
            setEncoding={setEncoding}
            setHasHeader={setHasHeader}
          />
        )}
        {/\.(sqlite|sqlite3|db)$/i.test(filename) && (
          <SqliteSettings tableName={tableName} setTableName={setTableName} disabled={pending} />
        )}
        {/\.xlsx$/i.test(filename) && (
          <XlsxSettings
            worksheet={worksheet}
            setWorksheet={setWorksheet}
            hasHeader={hasHeader}
            setHasHeader={setHasHeader}
            disabled={pending}
          />
        )}
      </div>
      <ErrorNotice error={error} />
      <button disabled={pending}>
        {pending ? 'Import wird vorgemerkt …' : 'Gespeicherte Datei erneut importieren'}
      </button>
    </form>
  );
}

function DatasetDetail({ session, id }: { session: Session; id: string }) {
  const [incomingPreview, setIncomingPreview] = useState<JobView>();
  const [revision, setRevision] = useState(0);
  const { data, error } = useLoad<DatasetView>('/datasets/' + id, revision, true);
  const [selected, setSelected] = useState<number>();
  const [actionError, setActionError] = useState<unknown>();
  const [exportInfo, setExportInfo] = useState('');
  const [exportPending, setExportPending] = useState(false);
  const latestImport = data?.jobs.find((job) => job.kind === 'IMPORT');
  const visibleJobs =
    data?.jobs.filter(
      (job) =>
        job.status !== 'SUCCEEDED' &&
        (job.kind !== 'IMPORT' || (!data.current_version && job.id === latestImport?.id)),
    ) ?? [];
  const oldImports =
    data?.jobs.filter(
      (job) =>
        job.kind === 'IMPORT' &&
        ['FAILED', 'CANCELLED'].includes(job.status) &&
        !visibleJobs.includes(job),
    ) ?? [];
  const queued = data?.jobs.some((job) => ['QUEUED', 'RUNNING'].includes(job.status));
  useEffect(() => {
    if (!queued) return;
    const timer = window.setTimeout(() => setRevision((v) => v + 1), 1500);
    return () => window.clearTimeout(timer);
  }, [queued, revision]);
  const version = data?.versions.find((v) => v.version_no === selected) ?? data?.versions[0];
  async function download(path: string) {
    setActionError(undefined);
    setExportPending(true);
    try {
      let info: { content_hash: string; protected_cells: number } | undefined;
      if (path !== '/original') {
        info = await request('/datasets/' + id + path + '-info');
      } else {
        await request('/datasets/' + id);
      }
      const anchor = document.createElement('a');
      anchor.href = '/api/v1/datasets/' + id + path;
      anchor.download = '';
      document.body.append(anchor);
      anchor.click();
      anchor.remove();
      setExportInfo(
        info
          ? 'CSV-Download gestartet. Geschützte Zellen: ' +
              info.protected_cells +
              '. Export-SHA-256: ' +
              info.content_hash
          : 'Download der unveränderten Originalbytes gestartet (.txt-Datei).',
      );
    } catch (e) {
      setActionError(e);
    } finally {
      setExportPending(false);
    }
  }
  if (!data)
    return (
      <>
        <ErrorNotice error={error} retry={() => setRevision((v) => v + 1)} />
        {!error && <Loading />}
      </>
    );
  return (
    <section>
      <header className="page-header">
        <div>
          <a href="#/daten">← Zur Datenwerkstatt</a>
          <p className="eyebrow">Datenintelligenz / Datensatz</p>
          <h1>{data.name}</h1>
          <p>
            {data.filename} · {data.original_bytes.toLocaleString('de-DE')} Originalbytes
          </p>
        </div>
        <span className="version-tag">
          {data.current_version
            ? 'Aktuell: Version ' + data.current_version
            : 'Noch keine Datenversion'}
        </span>
      </header>
      {version && (
        <SectionNav
          items={[
            { id: 'dataset-analysis', label: 'Analyse' },
            { id: 'dataset-rows', label: 'Datentabelle' },
            { id: 'dataset-quality', label: 'Qualität & Statistik' },
            ...(canWrite(session) && version.version_no === data.current_version
              ? [{ id: 'dataset-cleaning', label: 'Bereinigung' }]
              : []),
            { id: 'dataset-origin', label: 'Herkunft' },
          ]}
        />
      )}
      <ErrorNotice error={actionError} />
      <ErrorNotice error={error} />
      {visibleJobs.length > 0 && (
        <section className="form-card">
          <h2>Verarbeitung</h2>
          {visibleJobs.map((job) => (
            <div
              className={job.status === 'FAILED' ? 'notice error' : 'notice info'}
              key={job.id}
              role={job.status === 'FAILED' ? 'alert' : 'status'}
            >
              <strong>
                {job.kind === 'IMPORT' ? 'Import' : 'Vorschau'}: {jobLabels[job.status]}
              </strong>
              {job.status === 'RUNNING' && (
                <>
                  <progress aria-label="Verarbeitungsfortschritt" max={100} value={job.progress} />
                  <p>
                    {job.progress} % · {job.progress_message} ·{' '}
                    {job.processed_rows.toLocaleString('de-DE')} Zeilen
                  </p>
                </>
              )}
              {canWrite(session) && ['QUEUED', 'RUNNING'].includes(job.status) && (
                <button
                  className="secondary"
                  onClick={() => {
                    void request('/datasets/' + id + '/jobs/' + job.id + '/cancel', {
                      method: 'POST',
                      csrf: session.csrf_token,
                    })
                      .then(() => setRevision((v) => v + 1))
                      .catch(setActionError);
                  }}
                >
                  Auftrag abbrechen
                </button>
              )}
              <p>
                {job.error ??
                  'Der Hintergrundworker übernimmt diesen gespeicherten Auftrag automatisch.'}
              </p>
            </div>
          ))}
          <button className="secondary" onClick={() => setRevision((v) => v + 1)}>
            Status aktualisieren
          </button>
        </section>
      )}
      {!data.current_version &&
        !queued &&
        canWrite(session) &&
        latestImport &&
        ['FAILED', 'CANCELLED'].includes(latestImport.status) && (
          <RetryImport
            session={session}
            id={id}
            filename={data.filename}
            onQueued={() => setRevision((v) => v + 1)}
          />
        )}
      {oldImports.length > 0 && (
        <details className="form-card">
          <summary>Frühere Importversuche ({oldImports.length})</summary>
          <p>Die Originaldatei und frühere Fehlermeldungen bleiben als Historie erhalten.</p>
          {oldImports.map((job) => (
            <p key={job.id}>
              {date(job.created_at)} · {job.error}
            </p>
          ))}
        </details>
      )}
      {version && (
        <>
          <section className="form-card" id="dataset-analysis" tabIndex={-1}>
            <div className="section-heading">
              <h2>Gespeicherte Datenversion</h2>
              <Field label="Datenversion">
                <select
                  value={version.version_no}
                  onChange={(e) => {
                    setSelected(Number(e.target.value));
                    setExportInfo('');
                  }}
                >
                  {data.versions.map((v) => (
                    <option key={v.version_no} value={v.version_no}>
                      Version {v.version_no}
                      {v.source_version
                        ? ' · aus Version ' + v.source_version
                        : ' · Originalimport'}
                    </option>
                  ))}
                </select>
              </Field>
            </div>
            <details className="version-metadata">
              <summary>Metadaten und Prüfsumme</summary>
              <p className="data-hash">Daten-SHA-256: {version.content_hash}</p>
              <p>
                Erstellt: {date(version.created_at)} · Profilverfahren:{' '}
                {version.profile.profiling_version} · Pipeline: {version.profile.pipeline_version}
              </p>
              {version.steps.length > 0 && (
                <ol>
                  {version.steps.map((step, i) => (
                    <li key={i}>
                      {stepLabels[step.operation]}
                      {step.column ? ' · ' + step.column : ''}
                      {step.value !== null ? ' → ' + step.value : ''}
                    </li>
                  ))}
                </ol>
              )}
            </details>
            {['json', 'jsonl'].includes(version.profile.source_format) && (
              <p className="format-line">
                Quelle: {version.profile.source_format.toUpperCase()} · UTF-8 · Flache Tabelle;
                fehlende Schlüssel und null sind leere Zellen. Originalbytes bleiben erhalten.
              </p>
            )}
            {version.profile.source_format === 'sqlite' && (
              <p className="form-hint">
                Quelle: SQLite · Tabelle {version.profile.source_table} · unveränderlicher Snapshot;
                NULL als leere Zelle.
              </p>
            )}
            {version.profile.source_format === 'parquet' && (
              <p className="format-line">
                Quelle: Parquet · Spalten aus dem Dateischema; native Werte als Text, null als leere
                Zellen. Originalbytes bleiben erhalten.
              </p>
            )}
            {version.profile.source_format === 'xlsx' && (
              <p className="format-line">
                Quelle: XLSX · Arbeitsblatt {version.profile.source_worksheet} · Zellwerte;
                Datumswerte im ISO-Format. Die Originaldatei bleibt unverändert.
              </p>
            )}
            {version.profile.import_info && (
              <p className="format-line">
                Import erkannt:{' '}
                {(
                  {
                    ',': 'Komma',
                    ';': 'Semikolon',
                    '\t': 'Tabulator',
                    '|': 'Senkrechter Strich',
                  } as Record<string, string>
                )[version.profile.import_info.delimiter] ?? version.profile.import_info.delimiter}
                {' · '}
                {version.profile.import_info.encoding}
                {' · '}
                {version.profile.import_info.has_header
                  ? 'Erste Zeile als Kopfzeile'
                  : 'Spaltennamen automatisch erzeugt'}
                {version.profile.import_info.skipped_lines > 0 &&
                  ' · Einleitende Leer-/sep=-Zeilen berücksichtigt'}
              </p>
            )}
            <Suspense fallback={<Loading />}>
              <DataCharts key={version.version_no} id={id} version={version} />
            </Suspense>
            <details>
              <summary>Qualitätsprofil im Detail</summary>
              <ProfilePanel key={version.version_no} profile={version.profile} />
            </details>
            <div id="dataset-rows" tabIndex={-1}>
              <DataRows key={version.version_no} id={id} version={version} />
            </div>
            <button
              className="secondary"
              disabled={exportPending}
              onClick={() => void download('/versions/' + version.version_no + '/export')}
            >
              Version {version.version_no} als CSV exportieren
            </button>
            <p className="form-hint">
              Export: UTF-8, Semikolon. Formelverdächtige Zellen erhalten ein Apostroph; der
              gespeicherte Datenstand bleibt unverändert.
            </p>
            {exportInfo && (
              <p className="notice info data-hash" role="status">
                {exportInfo}
              </p>
            )}
          </section>
          <AnalysisPanel
            key={'analysis-' + version.version_no}
            session={session}
            id={id}
            version={version}
          />
          {canWrite(session) && version.version_no === data.current_version && (
            <div id="dataset-cleaning" tabIndex={-1}>
              <PlanPanel
                key={'plan-' + version.version_no}
                session={session}
                id={id}
                version={version}
                onPreview={(job) => {
                  setIncomingPreview(job);
                  setRevision((v) => v + 1);
                  document.getElementById('manual-cleaning')?.focus();
                }}
              />
              <TransformPanel
                key={version.version_no}
                incomingPreview={incomingPreview}
                session={session}
                dataset={data}
                version={version}
                onCommitted={() => {
                  setSelected(undefined);
                  setRevision((v) => v + 1);
                }}
              />
            </div>
          )}
        </>
      )}
      <details className="form-card" id="dataset-origin" tabIndex={-1}>
        <summary>Herkunft und Originaldatei</summary>
        <p>Die Originaldatei bleibt bei jeder Bereinigung unverändert.</p>
        <p className="data-hash">Original-SHA-256: {data.original_hash}</p>
        <button
          className="secondary"
          disabled={exportPending}
          onClick={() => void download('/original')}
        >
          Originalbytes herunterladen
        </button>
        <p className="form-hint">
          Die .txt-Endung erlaubt die Prüfung als Text, bevor die Datei in einer Tabellenkalkulation
          geöffnet wird.
        </p>
      </details>
    </section>
  );
}

export function ProfilePanel({ profile }: { profile: DataProfile }) {
  const [columnName, setColumnName] = useState(profile.columns[0]?.name ?? '');
  const column = profile.columns.find((c) => c.name === columnName) ?? profile.columns[0];
  return (
    <div>
      <div className="data-metrics" aria-label="Datenqualität">
        <div>
          <strong>{profile.rows.toLocaleString('de-DE')}</strong>
          <span>Datenzeilen</span>
        </div>
        <div>
          <strong>{profile.missing_cells.toLocaleString('de-DE')}</strong>
          <span>Fehlende Zellen</span>
        </div>
        <div>
          <strong>{profile.duplicate_rows.toLocaleString('de-DE')}</strong>
          <span>Doppelte Zeilen</span>
        </div>
        <div>
          <strong>{profile.completeness_percent.replace('.', ',')} %</strong>
          <span>Vollständigkeit</span>
        </div>
      </div>
      <p className="form-hint">
        Vollständigkeit misst belegte Zellen. Duplikate sind zusätzliche vollständig gleiche Zeilen.
        Diese Werte prüfen keine fachliche Richtigkeit.
      </p>
      {profile.statistics_note && <p className="notice info">{profile.statistics_note}</p>}
      <div className="table-scroll">
        <table>
          <caption>Spaltenprofil</caption>
          <thead>
            <tr>
              <th>Spalte</th>
              <th>Erkannter Typ</th>
              <th>Fehlend</th>
              <th>Verschieden</th>
              <th>Minimum</th>
              <th>Maximum</th>
              <th>Mittelwert</th>
              <th>Ausreißerhinweise</th>
            </tr>
          </thead>
          <tbody>
            {profile.columns.map((c) => (
              <tr key={c.name}>
                <th>{c.name}</th>
                <td>{typeLabels[c.inferred_type]}</td>
                <td>{c.missing}</td>
                <td>{c.distinct}</td>
                <td>{statistic(c.minimum)}</td>
                <td>{statistic(c.maximum)}</td>
                <td>{statistic(c.mean)}</td>
                <td>{c.outliers ?? 'Nicht berechnet'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="form-hint">
        Historisches Profilverfahren: Ausreißerhinweise mit 1,5 × Quartilsabstand. Das aktuelle
        Streamingverfahren weist Ausreißer als „Nicht berechnet“ aus.
      </p>
      {column && (
        <div className="data-distribution">
          <Field label="Verteilung für Spalte">
            <select value={column.name} onChange={(e) => setColumnName(e.target.value)}>
              {profile.columns.map((c) => (
                <option key={c.name}>{c.name}</option>
              ))}
            </select>
          </Field>
          <h3>Häufigste Originalwerte</h3>
          <p className="form-hint">Bis zu acht Werte, leere Zellen ausgenommen.</p>
          {column.top_values.length === 0 ? (
            <p>Keine belegten Werte.</p>
          ) : (
            <ul>
              {column.top_values.map((item, index) => (
                <li key={index}>
                  <span>{item.value}</span>
                  <meter
                    aria-label={item.value + ': ' + item.count}
                    min={0}
                    max={Math.max(1, profile.rows)}
                    value={item.count}
                  />
                  <strong>{item.count}</strong>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}

function DataRows({ id, version }: { id: string; version: VersionView }) {
  const [offset, setOffset] = useState(0);
  const { data, error } = useLoad<{ columns: string[]; rows: string[][]; total: number }>(
    '/datasets/' + id + '/versions/' + version.version_no + '/rows?offset=' + offset,
  );
  return (
    <section>
      <h3>Datenansicht</h3>
      <ErrorNotice error={error} />
      {!data && !error ? (
        <Loading />
      ) : (
        data && (
          <>
            <DataTable columns={data.columns} rows={data.rows} />
            <div className="data-pagination">
              <button className="secondary" disabled={offset === 0} onClick={() => setOffset(0)}>
                Erste Zeilen
              </button>
              <button
                className="secondary"
                disabled={offset === 0}
                onClick={() => setOffset((v) => Math.max(0, v - 25))}
              >
                Vorherige Zeilen
              </button>
              <span>
                {(data.total ? offset + 1 : 0).toLocaleString('de-DE')}–
                {Math.min(offset + 25, data.total).toLocaleString('de-DE')} von{' '}
                {data.total.toLocaleString('de-DE')}
              </span>
              <button
                className="secondary"
                disabled={offset + 25 >= data.total}
                onClick={() => setOffset((v) => v + 25)}
              >
                Weitere Zeilen
              </button>
              <button
                className="secondary"
                disabled={offset + 25 >= data.total}
                onClick={() => setOffset(Math.max(0, Math.floor((data.total - 1) / 25) * 25))}
              >
                Letzte Zeilen
              </button>
            </div>
          </>
        )
      )}
    </section>
  );
}
function DataTable({ columns, rows }: { columns: string[]; rows: string[][] }) {
  return (
    <div className="table-scroll">
      <table>
        <thead>
          <tr>
            {columns.map((c) => (
              <th key={c}>{c}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i}>
              {row.map((value, j) => (
                <td className="data-cell" key={j}>
                  {value || <span className="muted">leer</span>}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function TransformPanel({
  session,
  dataset,
  version,
  onCommitted,
  incomingPreview,
}: {
  session: Session;
  dataset: DatasetView;
  version: VersionView;
  onCommitted: () => void;
  incomingPreview?: JobView;
}) {
  const [steps, setSteps] = useState<Step[]>([]);
  const [operation, setOperation] = useState<Step['operation']>('trim');
  const [column, setColumn] = useState(version.profile.columns[0]?.name ?? '');
  const [value, setValue] = useState('');
  const [job, setJob] = useState<JobView>();
  useEffect(() => {
    if (incomingPreview?.source_version === version.version_no) {
      setJob(incomingPreview);
      setSteps(incomingPreview.steps);
    }
  }, [incomingPreview, version.version_no]);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<unknown>();
  const usesColumn = !['drop_duplicates', 'drop_empty_rows'].includes(operation);
  useEffect(() => {
    if (!job || !['QUEUED', 'RUNNING'].includes(job.status)) return;
    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      request<JobView>('/datasets/' + dataset.id + '/jobs/' + job.id, { signal: controller.signal })
        .then((next) => {
          if (!controller.signal.aborted) setJob(next);
        })
        .catch((e: unknown) => {
          if (!controller.signal.aborted) {
            setError(e);
            setJob((current) => (current ? { ...current } : undefined));
          }
        });
    }, 1000);
    return () => {
      controller.abort();
      window.clearTimeout(timer);
    };
  }, [job, dataset.id]);
  async function calculate() {
    setPending(true);
    setError(undefined);
    setJob(undefined);
    try {
      setJob(
        await request<JobView>('/datasets/' + dataset.id + '/previews', {
          method: 'POST',
          csrf: session.csrf_token,
          body: { source_version: version.version_no, steps },
        }),
      );
    } catch (e) {
      setError(e);
    } finally {
      setPending(false);
    }
  }
  async function commit() {
    if (!job?.result_hash) return;
    setPending(true);
    setError(undefined);
    try {
      await request('/datasets/' + dataset.id + '/versions', {
        method: 'POST',
        csrf: session.csrf_token,
        body: {
          preview_id: job.id,
          result_hash: job.result_hash,
          expected_current_version: version.version_no,
        },
      });
      onCommitted();
    } catch (e) {
      setError(e);
    } finally {
      setPending(false);
    }
  }
  return (
    <section className="form-card">
      <h2 id="manual-cleaning" tabIndex={-1}>
        Bereinigung planen
      </h2>
      {dataset.jobs.some(
        (j) => j.kind === 'PREVIEW' && j.source_version === version.version_no,
      ) && (
        <Field label="Gespeicherte Vorschau erneut öffnen">
          <select
            value={job?.id ?? ''}
            disabled={pending}
            onChange={(event) => {
              const existing = dataset.jobs.find((j) => j.id === event.target.value);
              setJob(existing);
              setSteps(existing?.steps ?? []);
              setError(undefined);
            }}
          >
            <option value="">Neue Bereinigung planen</option>
            {dataset.jobs
              .filter((j) => j.kind === 'PREVIEW' && j.source_version === version.version_no)
              .map((j) => (
                <option key={j.id} value={j.id}>
                  {date(j.created_at)} · {jobLabels[j.status]} · {j.steps.length} Schritte
                </option>
              ))}
          </select>
        </Field>
      )}
      <p>
        Schritte werden in der angegebenen Reihenfolge auf Version {version.version_no} angewendet.
        Prüfe die Vorschau, bevor du einen neuen Stand speicherst.
      </p>
      <div className="data-fields">
        <Field label="Bereinigungsschritt">
          <select
            value={operation}
            disabled={pending}
            onChange={(e) => setOperation(e.target.value as Step['operation'])}
          >
            {Object.entries(stepLabels).map(([key, label]) => (
              <option key={key} value={key}>
                {label}
              </option>
            ))}
          </select>
        </Field>
        {usesColumn && (
          <Field label="Zielspalte">
            <select value={column} disabled={pending} onChange={(e) => setColumn(e.target.value)}>
              {version.profile.columns.map((c) => (
                <option key={c.name}>{c.name}</option>
              ))}
            </select>
          </Field>
        )}
        {operation === 'fill_missing' && (
          <Field label="Ersatzwert">
            <input
              value={value}
              maxLength={1000}
              disabled={pending}
              onChange={(e) => setValue(e.target.value)}
            />
          </Field>
        )}
      </div>
      <button
        className="secondary"
        disabled={pending || steps.length >= 10}
        onClick={() => {
          setSteps([
            ...steps,
            {
              operation,
              column: usesColumn ? column : null,
              value: operation === 'fill_missing' ? value : null,
            },
          ]);
          setJob(undefined);
        }}
      >
        Schritt hinzufügen
      </button>
      <ol className="data-steps">
        {steps.map((step, i) => (
          <li key={i}>
            <span>
              {stepLabels[step.operation]}
              {step.column ? ' · ' + step.column : ''}
              {step.value !== null ? ' → ' + step.value : ''}
            </span>
            <button
              className="text-button"
              disabled={pending}
              aria-label={'Schritt ' + (i + 1) + ' entfernen'}
              onClick={() => {
                setSteps(steps.filter((_, n) => n !== i));
                setJob(undefined);
              }}
            >
              Entfernen
            </button>
          </li>
        ))}
      </ol>
      <ErrorNotice error={error} />
      <button
        disabled={pending || !steps.length || (!!job && ['QUEUED', 'RUNNING'].includes(job.status))}
        onClick={() => void calculate()}
      >
        Vorschau berechnen
      </button>
      {job && ['QUEUED', 'RUNNING'].includes(job.status) && (
        <Loading text="Gespeicherte Vorschau wird berechnet …" />
      )}
      {job?.status === 'RUNNING' && (
        <div className="notice info" role="status">
          <progress aria-label="Vorschaufortschritt" max={100} value={job.progress} />
          <p>
            {job.progress} % · {job.progress_message}
          </p>
        </div>
      )}
      {job && ['QUEUED', 'RUNNING'].includes(job.status) && (
        <button
          className="secondary"
          onClick={() => {
            void request<JobView>('/datasets/' + dataset.id + '/jobs/' + job.id + '/cancel', {
              method: 'POST',
              csrf: session.csrf_token,
            })
              .then(setJob)
              .catch(setError);
          }}
        >
          Vorschau abbrechen
        </button>
      )}
      {job && ['FAILED', 'CANCELLED'].includes(job.status) && (
        <p role="alert" className="notice error">
          {job.error}
        </p>
      )}
      {job?.status === 'SUCCEEDED' && job.profile && (
        <section className="data-preview">
          <h3>Vorschau · noch nicht übernommen</h3>
          <p>
            Zeilen: {version.profile.rows} → {job.profile.rows} · Fehlwerte:{' '}
            {version.profile.missing_cells} → {job.profile.missing_cells} · Duplikate:{' '}
            {version.profile.duplicate_rows} → {job.profile.duplicate_rows}
          </p>
          <p className="data-hash">Vorschau-SHA-256: {job.result_hash}</p>
          <DataTable columns={job.profile.columns.map((c) => c.name)} rows={job.profile.sample} />
          <p className="form-hint">
            Erste 25 Ergebniszeilen; Kennzahlen und Prüfsumme beziehen sich auf das gesamte
            Ergebnis.
          </p>
          <button disabled={pending} onClick={() => void commit()}>
            Vorschau bestätigen und Version {version.version_no + 1} speichern
          </button>
        </section>
      )}
    </section>
  );
}
