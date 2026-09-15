import { useEffect, useRef, useState } from 'react';
import { ApiError, request } from './api';
import { Empty, ErrorNotice, Loading } from './components';
import { date, roles } from './format';
import type { Page, Scenario, Session } from './types';
import { useLoad } from './useLoad';
import { ScenarioForm } from './ScenarioForm';
import { ScenarioPage } from './ScenarioPage';
import { ResultPage } from './Result';
import { Compare } from './Compare';
import { Audit, Members } from './Admin';
import { DataWorkspace } from './DataWorkspace';
import { Brand, DensityControl, Icon, TableToolbar, WorkspaceSummary } from './DesignSystem';

const route = () => window.location.hash.slice(1) || '/szenarien';
function navigate(path: string) {
  window.location.hash = path;
  window.scrollTo({ top: 0 });
}

export function App() {
  const [session, setSession] = useState<Session | null>();
  const [error, setError] = useState<unknown>();
  const [path, setPath] = useState(route);
  const [navigationOpen, setNavigationOpen] = useState(false);
  const navigationToggle = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    const listener = () => {
      setPath(route());
      window.scrollTo({ top: 0 });
    };
    window.addEventListener('hashchange', listener);
    return () => window.removeEventListener('hashchange', listener);
  }, []);
  useEffect(() => {
    void refresh();
  }, []);
  async function refresh() {
    setSession(undefined);
    setError(undefined);
    try {
      setSession(await request<Session>('/me'));
      setError(undefined);
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) {
        setSession(null);
        setError(undefined);
      } else {
        setSession(undefined);
        setError(e);
      }
    }
  }
  async function logout() {
    try {
      if (session) await request('/auth/logout', { method: 'POST', csrf: session.csrf_token });
      setSession(null);
      navigate('/szenarien');
    } catch (e) {
      setError(e);
    }
  }
  if (session === undefined)
    return (
      <main className="standalone">
        <ErrorNotice error={error} retry={() => void refresh()} />
        {!error && <Loading text="Sitzung wird geprüft …" />}
      </main>
    );
  if (!session)
    return (
      <main className="login-page">
        <div className="brand">
          <Brand />
        </div>
        <div className="login-content">
          <p className="eyebrow">Architektur · Daten · Entscheidungen</p>
          <h1>
            Ein klarer Blick.
            <br />
            Eine belastbare Entscheidung.
          </h1>
          <p>
            Architekturen bewerten, Daten untersuchen und Änderungen nachvollziehbar freigeben. Ein
            gemeinsamer Arbeitsbereich für Analyse und Umsetzung.
          </p>
          <a className="button" href="/api/v1/auth/login">
            Sicher anmelden <span aria-hidden="true">↗</span>
          </a>
          <p className="form-hint">Lokale Demo · Anmeldung über dein Organisationskonto</p>
          <ErrorNotice error={error} />
        </div>
        <div className="login-graphic" aria-hidden="true">
          <span>ARBEITSBEREICHE</span>
          <div>
            <b>01</b>
            <strong>Architekturplanung</strong>
            <small>Anforderungen · Alternativen · Kosten</small>
          </div>
          <div>
            <b>02</b>
            <strong>Datenintelligenz</strong>
            <small>Import · Analyse · Versionierung</small>
          </div>
          <div>
            <b>03</b>
            <strong>Nachweise & Kontrolle</strong>
            <small>Herkunft · Berechtigungen · Audit</small>
          </div>
        </div>
      </main>
    );
  if (!session.organization)
    return (
      <main className="standalone">
        <div className="brand">
          <Brand />
        </div>
        <h1>Organisation auswählen</h1>
        <p>
          Angemeldet als {session.user.display_name}. Wähle den Arbeitsbereich für diese Sitzung.
        </p>
        <OrganizationChoice session={session} refresh={refresh} />
        <button className="text-button" onClick={() => void logout()}>
          Abmelden
        </button>
      </main>
    );
  return (
    <div className="app-shell">
      <a
        className="skip-link"
        href="#main-content"
        onClick={(event) => {
          event.preventDefault();
          document.getElementById('main-content')?.focus();
        }}
      >
        Zum Inhalt springen
      </a>
      <aside className="sidebar">
        <a href="#/szenarien" className="brand">
          <Brand />
        </a>
        <button
          className="navigation-toggle"
          ref={navigationToggle}
          aria-expanded={navigationOpen}
          aria-controls="workspace-navigation"
          onClick={() => setNavigationOpen(!navigationOpen)}
        >
          <Icon name={navigationOpen ? 'close' : 'menu'} /> Navigation
        </button>
        <a
          href="#/organisation"
          className="org-label"
          aria-label={'Arbeitsbereich wechseln: ' + session.organization.name}
        >
          <small>Aktiver Arbeitsbereich</small>
          <strong>{session.organization.name}</strong>
          <Icon name="chevron" />
        </a>
        <nav
          id="workspace-navigation"
          data-open={navigationOpen}
          aria-label="Hauptnavigation"
          onClick={(event) => {
            if ((event.target as Element).closest('a')) {
              setNavigationOpen(false);
              if (navigationOpen)
                requestAnimationFrame(() => document.getElementById('main-content')?.focus());
            }
          }}
          onKeyDown={(event) => {
            if (event.key === 'Escape') {
              setNavigationOpen(false);
              navigationToggle.current?.focus();
            }
          }}
        >
          <p className="nav-section">
            <span>01</span> Architekturplanung
          </p>
          <a
            href="#/szenarien"
            aria-current={
              path === '/szenarien' ||
              path.startsWith('/szenario/') ||
              path.startsWith('/bewertung/') ||
              path === '/neu'
                ? 'page'
                : undefined
            }
          >
            <Icon name="scenarios" />
            Szenarien
          </a>
          <a href="#/vergleich" aria-current={path === '/vergleich' ? 'page' : undefined}>
            <Icon name="compare" />
            Vergleich
          </a>
          <p className="nav-section">
            <span>02</span> Datenintelligenz
          </p>
          <a
            href="#/daten"
            aria-current={path === '/daten' || path.startsWith('/daten/') ? 'page' : undefined}
          >
            <Icon name="data" />
            Datenwerkstatt
          </a>
          {session.roles.includes('ORG_ADMIN') && (
            <>
              <p className="nav-section">
                <span>03</span> Verwaltung
              </p>
              <a href="#/audit" aria-current={path === '/audit' ? 'page' : undefined}>
                <Icon name="audit" />
                Audit-Protokoll
              </a>
              <a href="#/mitglieder" aria-current={path === '/mitglieder' ? 'page' : undefined}>
                <Icon name="people" />
                Mitglieder & Rechte
              </a>
            </>
          )}
        </nav>
        <div className="sidebar-bottom">
          <span className="demo-environment">Lokale Demo</span>
          <p>
            Nachvollziehbar arbeiten.
            <br />
            Originale bewahren.
          </p>
          <a href="#/organisation">Arbeitsbereich wechseln</a>
        </div>
      </aside>
      <div className="workspace">
        <header className="topbar">
          <span className="workspace-context">
            <Icon
              name={
                path.startsWith('/daten')
                  ? 'data'
                  : path === '/organisation'
                    ? 'people'
                    : 'scenarios'
              }
            />
            <span aria-hidden="true">/</span>{' '}
            <strong>
              {path.startsWith('/daten')
                ? 'Datenintelligenz'
                : ['/audit', '/mitglieder', '/organisation'].includes(path)
                  ? 'Verwaltung'
                  : 'Architekturplanung'}
            </strong>
          </span>
          <DensityControl />
          <div className="session-identity">
            <strong>{session.user.display_name}</strong>
            <small>{session.roles.map((r) => roles[r]).join(' · ')}</small>
          </div>
          <button className="text-button" onClick={() => void logout()}>
            Abmelden
          </button>
        </header>
        <main id="main-content" tabIndex={-1} key={session.organization.id}>
          <ErrorNotice error={error} />
          {path === '/organisation' ? (
            <section>
              <h1>Arbeitsbereich wechseln</h1>
              <OrganizationChoice session={session} refresh={refresh} />
            </section>
          ) : path === '/neu' && session.roles.some((r) => r !== 'VIEWER') ? (
            <ScenarioForm
              session={session}
              onSaved={(s) => navigate('/szenario/' + s.id)}
              onCancel={() => navigate('/szenarien')}
            />
          ) : path.startsWith('/szenario/') ? (
            <ScenarioPage
              key={path}
              id={path.split('/')[2]}
              session={session}
              navigate={navigate}
            />
          ) : path.startsWith('/bewertung/') ? (
            <ResultPage
              key={path}
              id={path.split('/')[2]}
              session={session}
              onBack={() => navigate('/vergleich')}
            />
          ) : path === '/daten' || path.startsWith('/daten/') ? (
            <DataWorkspace session={session} id={path.split('/')[2]} navigate={navigate} />
          ) : path === '/vergleich' ? (
            <Compare navigate={navigate} />
          ) : path === '/audit' && session.roles.includes('ORG_ADMIN') ? (
            <Audit />
          ) : path === '/mitglieder' && session.roles.includes('ORG_ADMIN') ? (
            <Members session={session} refreshSession={refresh} />
          ) : (
            <ScenarioList session={session} />
          )}
        </main>
        <footer>
          <span>
            IT-KOMPASS <span aria-hidden="true">/</span> Arbeitskonsole
          </span>
          <span>Synthetische Beispielpreise · Unveränderliche Versionsstände</span>
        </footer>
      </div>
    </div>
  );
}

function OrganizationChoice({
  session,
  refresh,
}: {
  session: Session;
  refresh: () => Promise<void>;
}) {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<unknown>();
  async function choose(id: string) {
    setPending(true);
    setError(undefined);
    try {
      await request('/session/organization', {
        method: 'POST',
        csrf: session.csrf_token,
        body: { organization_id: id },
      });
      await refresh();
      navigate('/szenarien');
    } catch (e) {
      setError(e);
    } finally {
      setPending(false);
    }
  }
  return (
    <div className="organization-list">
      <ErrorNotice error={error} />
      {session.organizations.length ? (
        session.organizations.map((org) => (
          <button
            key={org.id}
            className="organization-button"
            disabled={pending}
            onClick={() => void choose(org.id)}
          >
            <strong>{org.name}</strong>
            <small>{org.roles.map((r) => roles[r]).join(' · ')}</small>
            <span aria-hidden="true">→</span>
          </button>
        ))
      ) : (
        <p>
          Deine Identität hat keine aktive Organisationszuordnung. Eine Administration muss die
          Zuordnung einrichten.
        </p>
      )}
    </div>
  );
}
function ScenarioList({ session }: { session: Session }) {
  const { data, error } = useLoad<Page<Scenario>>('/scenarios?limit=25');
  const [extra, setExtra] = useState<Scenario[]>([]);
  const [cursor, setCursor] = useState<string | null | undefined>(undefined);
  const [loadError, setLoadError] = useState<unknown>();
  const [pending, setPending] = useState(false);
  const canWrite = session.roles.some((role) => role !== 'VIEWER');
  const all = [...(data?.items ?? []), ...extra];
  const [query, setQuery] = useState('');
  const shown = all.filter((s) =>
    (s.name + ' ' + s.version.data.company_profile.industry)
      .toLocaleLowerCase('de')
      .includes(query.toLocaleLowerCase('de')),
  );
  async function more() {
    const next = cursor === undefined ? data?.next_cursor : cursor;
    if (!next) return;
    setPending(true);
    try {
      const page = await request<Page<Scenario>>(
        '/scenarios?limit=25&cursor=' + encodeURIComponent(next),
      );
      setExtra((v) => [...v, ...page.items]);
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
          <p className="eyebrow">Planung & Bewertung</p>
          <h1>Szenarien</h1>
          <p>Von deinen Anforderungen zur begründeten Architekturentscheidung.</p>
        </div>
        {canWrite && (
          <button onClick={() => navigate('/neu')}>
            <Icon name="plus" /> Neues Szenario
          </button>
        )}
      </header>
      <WorkspaceSummary
        items={[
          { label: 'Szenarien', value: data ? all.length : '—', hint: 'Im geladenen Bestand' },
          {
            label: 'Arbeitslasten',
            value: data ? all.reduce((sum, s) => sum + s.version.data.workloads.length, 0) : '—',
            hint: 'In diesen Szenarien',
          },
          {
            label: 'Weiterentwickelt',
            value: data ? all.filter((s) => s.current_version > 1).length : '—',
            hint: 'Mehr als ein Profilstand',
          },
        ]}
      />
      <ErrorNotice error={error ?? loadError} />
      <section className="form-card catalog-panel">
        <div className="section-heading">
          <h2>Unternehmensszenarien</h2>
          <span className="muted">{all.length} geladen</span>
        </div>
        <TableToolbar
          label="Geladene Szenarien filtern"
          query={query}
          onQuery={setQuery}
          count={shown.length}
          total={all.length}
        />
        {!data && !error ? (
          <Loading />
        ) : all.length === 0 ? (
          <Empty title="Ein guter Plan beginnt hier.">
            <p>
              Lege dein erstes Szenario an. Ein bearbeitbares, synthetisches Beispiel hilft dir beim
              Einstieg.
            </p>
            {canWrite && (
              <button className="secondary" onClick={() => navigate('/neu')}>
                Erstes Szenario anlegen
              </button>
            )}
          </Empty>
        ) : (
          <div className="table-scroll">
            <table className="catalog-table scenario-catalog">
              <caption className="sr-only">Unternehmensszenarien im geladenen Bestand</caption>
              <thead>
                <tr>
                  <th>Szenario</th>
                  <th>Branche</th>
                  <th>Arbeitslasten</th>
                  <th>Profilstand</th>
                  <th>Erstellt</th>
                  <th>Aktion</th>
                </tr>
              </thead>
              <tbody>
                {shown.map((s) => (
                  <tr key={s.id}>
                    <th scope="row">
                      <span className="record-name">
                        <Icon name="scenarios" />
                        {s.name}
                      </span>
                    </th>
                    <td>{s.version.data.company_profile.industry}</td>
                    <td>{s.version.data.workloads.length}</td>
                    <td>
                      <span className="version-tag">Version {s.current_version}</span>
                    </td>
                    <td>{date(s.created_at)}</td>
                    <td>
                      <button className="text-button" onClick={() => navigate('/szenario/' + s.id)}>
                        Öffnen →
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {shown.length === 0 && (
              <p className="table-no-results">Keine geladenen Szenarien passen zum Filter.</p>
            )}
          </div>
        )}
        {(cursor === undefined ? data?.next_cursor : cursor) && (
          <button className="secondary" disabled={pending} onClick={() => void more()}>
            Weitere Szenarien laden
          </button>
        )}
      </section>
      <div className="notice info">
        <strong>Eine nachvollziehbare Modellrechnung</strong>
        <p>
          Vier Demo-Alternativen, klare Ausschlussregeln und unveränderliche Ergebnisse. Ein
          unbekannter Wert wird nicht als null gerechnet.
        </p>
      </div>
    </section>
  );
}
