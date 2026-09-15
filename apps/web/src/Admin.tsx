import { useState } from 'react';
import type { FormEvent } from 'react';
import { request } from './api';
import { Badge, ErrorNotice, Field, Loading } from './components';
import { date, roles } from './format';
import type { AuditEvent, Member, Page, Role, Session } from './types';
import { useLoad } from './useLoad';

const roleKeys = Object.keys(roles) as Role[];
function MemberEditor({
  member,
  session,
  onChanged,
}: {
  member: Member;
  session: Session;
  onChanged: () => void;
}) {
  const [chosen, setChosen] = useState(member.roles);
  const [status, setStatus] = useState(member.status);
  const [error, setError] = useState<unknown>();
  const [pending, setPending] = useState(false);
  async function save(event: FormEvent) {
    event.preventDefault();
    setPending(true);
    setError(undefined);
    try {
      await request('/organizations/current/members/' + member.user_id, {
        method: 'PATCH',
        csrf: session.csrf_token,
        body: { roles: chosen, status, expected_revision: member.revision },
      });
      onChanged();
    } catch (e) {
      setError(e);
    } finally {
      setPending(false);
    }
  }
  return (
    <form className="member-card" onSubmit={(e) => void save(e)}>
      <h3>{member.user_id === session.user.id ? 'Deine Mitgliedschaft' : 'Mitglied'}</h3>
      <code>{member.user_id}</code>
      <Badge value={member.status} />
      <fieldset disabled={pending}>
        <div className="role-fields">
          {roleKeys.map((role) => (
            <label key={role}>
              <input
                type="checkbox"
                checked={chosen.includes(role)}
                onChange={(e) =>
                  setChosen(e.target.checked ? [...chosen, role] : chosen.filter((r) => r !== role))
                }
              />
              {roles[role]}
            </label>
          ))}
        </div>
        <Field label="Mitgliedschaftsstatus">
          <select value={status} onChange={(e) => setStatus(e.target.value as Member['status'])}>
            <option value="ACTIVE">Aktiv</option>
            <option value="REVOKED">Gesperrt</option>
          </select>
        </Field>
        <button className="secondary" disabled={chosen.length === 0}>
          Änderungen speichern
        </button>
      </fieldset>
      <ErrorNotice error={error} />
    </form>
  );
}
export function Members({
  session,
  refreshSession,
}: {
  session: Session;
  refreshSession: () => Promise<void>;
}) {
  const [revision, setRevision] = useState(0);
  const { data, error } = useLoad<Page<Member>>('/organizations/current/members', revision);
  const [userId, setUserId] = useState('');
  const [role, setRole] = useState<Role>('VIEWER');
  const [formError, setFormError] = useState<unknown>();
  const [pending, setPending] = useState(false);
  function changed() {
    setRevision((v) => v + 1);
    void refreshSession();
  }
  async function add(event: FormEvent) {
    event.preventDefault();
    setPending(true);
    setFormError(undefined);
    try {
      await request('/organizations/current/members', {
        method: 'POST',
        csrf: session.csrf_token,
        body: { user_id: userId, roles: [role] },
      });
      setUserId('');
      changed();
    } catch (e) {
      setFormError(e);
    } finally {
      setPending(false);
    }
  }
  return (
    <section>
      <header className="page-header">
        <div>
          <p className="eyebrow">Organisation</p>
          <h1>Mitglieder & Rechte</h1>
          <p>
            Rollen gelten ausschließlich für {session.organization?.name}. Die letzte aktive
            Administrationsrolle bleibt geschützt.
          </p>
        </div>
      </header>
      <ErrorNotice error={error} />
      <div className="member-grid">
        {data
          ? data.items.map((m) => (
              <MemberEditor
                key={m.user_id + ':' + m.revision}
                member={m}
                session={session}
                onChanged={changed}
              />
            ))
          : !error && <Loading />}
      </div>
      <form className="form-card" onSubmit={(e) => void add(e)}>
        <h2>Vorhandene Identität zuordnen</h2>
        <p>
          Trage die interne Nutzerkennung einer bereits zugeordneten OIDC-Identität ein. Es gibt
          keine freie Registrierung oder öffentliche Nutzersuche.
        </p>
        <fieldset disabled={pending}>
          <div className="form-grid">
            <Field label="Interne Nutzerkennung (UUID)">
              <input
                required
                pattern="[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
                value={userId}
                onChange={(e) => setUserId(e.target.value)}
              />
            </Field>
            <Field label="Anfangsrolle">
              <select value={role} onChange={(e) => setRole(e.target.value as Role)}>
                {roleKeys.map((r) => (
                  <option key={r} value={r}>
                    {roles[r]}
                  </option>
                ))}
              </select>
            </Field>
          </div>
          <button className="secondary">Mitglied zuordnen</button>
        </fieldset>
        <ErrorNotice error={formError} />
      </form>
    </section>
  );
}
export function Audit() {
  const [cursor, setCursor] = useState<string | null>(null);
  return (
    <section>
      <header className="page-header">
        <div>
          <p className="eyebrow">Nachvollziehbarkeit</p>
          <h1>Audit-Protokoll</h1>
          <p>Fachliche Änderungen und Nachweise der aktiven Organisation.</p>
        </div>
      </header>
      <AuditPage key={cursor ?? 'first'} cursor={cursor} next={setCursor} />
    </section>
  );
}
function AuditPage({
  cursor,
  next,
}: {
  cursor: string | null;
  next: (cursor: string | null) => void;
}) {
  const { data, error } = useLoad<Page<AuditEvent>>(
    '/audit-events?limit=25' + (cursor ? '&cursor=' + encodeURIComponent(cursor) : ''),
  );
  return (
    <div className="form-card">
      <ErrorNotice error={error} />
      {data ? (
        <>
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Zeitpunkt</th>
                  <th>Aktion</th>
                  <th>Urheber</th>
                  <th>Nachweis</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((item) => (
                  <tr key={item.id}>
                    <th>{date(item.created_at)}</th>
                    <td>{item.event_type}</td>
                    <td>
                      <code>{item.actor_user_id}</code>
                    </td>
                    <td>
                      <details>
                        <summary>{item.entity_type}</summary>
                        <pre>
                          {JSON.stringify({ id: item.entity_id, ...item.metadata }, null, 2)}
                        </pre>
                      </details>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {data.items.length === 0 && <p>Noch keine fachlichen Ereignisse.</p>}
          <div className="form-actions">
            {cursor && (
              <button className="secondary" onClick={() => next(null)}>
                Zum Anfang
              </button>
            )}
            {data.next_cursor && (
              <button className="secondary" onClick={() => next(data.next_cursor ?? null)}>
                Weitere Ereignisse
              </button>
            )}
          </div>
        </>
      ) : (
        !error && <Loading />
      )}
    </div>
  );
}
