import { useState } from 'react';
import type { FormEvent } from 'react';
import { request } from './api';
import { Field, ErrorNotice } from './components';
import { decimal, integer } from './format';
import type { Scenario, ScenarioInput, Session, Workload, Asset } from './types';

export function emptyWorkload(): Workload {
  return {
    workload_key: 'last_' + crypto.randomUUID().slice(0, 8),
    name: '',
    workload_type: 'BUSINESS_APP',
    user_count: null,
    vcpu_count: null,
    memory_gib: null,
    storage_gib: null,
    max_latency_ms: null,
    availability_percent: null,
    rto_seconds: null,
    rpo_seconds: null,
    sensitivity: null,
    internet_dependency_allowed: null,
  };
}
export function emptyScenario(): ScenarioInput {
  return {
    name: '',
    company_profile: {
      industry: '',
      employee_count: null,
      it_staff_fte: null,
      monthly_budget: null,
      initial_budget: null,
      currency: 'EUR',
    },
    workloads: [emptyWorkload()],
    infrastructure_assets: [],
    requirements: { region: 'EU', hard_budget: false },
  };
}
const workloadTypes = {
  BUSINESS_APP: 'Geschäftsanwendung',
  WEB_APP: 'Webanwendung',
  DATABASE: 'Datenbank',
  FILE_STORAGE: 'Dateiablage',
  ANALYTICS: 'Datenanalyse',
  OTHER: 'Sonstige Arbeitslast',
};
const sensitivity = {
  PUBLIC: 'Öffentlich',
  INTERNAL: 'Intern',
  CONFIDENTIAL: 'Vertraulich',
  RESTRICTED: 'Streng vertraulich',
};
const assetTypes = {
  SERVER: 'Server',
  STORAGE: 'Speicher',
  NETWORK: 'Netzwerk',
  LICENSE: 'Lizenz',
  OTHER: 'Sonstiges',
};

export function ScenarioForm({
  session,
  scenario,
  onSaved,
  onCancel,
}: {
  session: Session;
  scenario?: Scenario;
  onSaved: (value: Scenario) => void;
  onCancel: () => void;
}) {
  const [data, setData] = useState<ScenarioInput>(() =>
    scenario ? structuredClone(scenario.version.data) : emptyScenario(),
  );
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<unknown>();
  const [demoLoaded, setDemoLoaded] = useState(false);
  function patchWorkload(index: number, values: Partial<Workload>) {
    setData((current) => ({
      ...current,
      workloads: current.workloads.map((w, i) => (i === index ? { ...w, ...values } : w)),
    }));
  }
  function patchAsset(index: number, values: Partial<Asset>) {
    setData((current) => ({
      ...current,
      infrastructure_assets: current.infrastructure_assets.map((a, i) =>
        i === index ? { ...a, ...values } : a,
      ),
    }));
  }
  async function demo() {
    setPending(true);
    setError(undefined);
    try {
      setData(await request<ScenarioInput>('/demo-scenario'));
      setDemoLoaded(true);
    } catch (e) {
      setError(e);
    } finally {
      setPending(false);
    }
  }
  async function save(event: FormEvent) {
    event.preventDefault();
    setPending(true);
    setError(undefined);
    try {
      const result = await request<Scenario>(
        scenario ? '/scenarios/' + scenario.id + '/versions' : '/scenarios',
        {
          method: 'POST',
          csrf: session.csrf_token,
          body: scenario ? { ...data, expected_current_version: scenario.current_version } : data,
        },
      );
      onSaved(result);
    } catch (e) {
      setError(e);
    } finally {
      setPending(false);
    }
  }
  return (
    <section>
      <header className="page-header">
        <div>
          <p className="eyebrow">Unternehmensaufnahme</p>
          <h1>{scenario ? 'Szenario bearbeiten' : 'Neues Szenario'}</h1>
          <p>
            {scenario
              ? 'Änderungen werden als neue Version gespeichert. Frühere Bewertungen bleiben erhalten.'
              : 'Ein klar beschriebenes Szenario ist die Grundlage für einen belastbaren Vergleich.'}
          </p>
        </div>
        {!scenario && (
          <button
            className="secondary"
            type="button"
            onClick={() => void demo()}
            disabled={pending}
          >
            Synthetisches Beispiel laden
          </button>
        )}
      </header>
      <form onSubmit={(event) => void save(event)}>
        <ErrorNotice error={error} />
        {demoLoaded && (
          <div className="notice info" role="status">
            Synthetisches Beispiel geladen. Du kannst sämtliche Angaben vor dem Speichern
            bearbeiten.
          </div>
        )}
        <fieldset disabled={pending} className="form-card">
          <legend>
            <span className="step-number">01</span> Unternehmen & Rahmen
          </legend>
          <div className="form-grid">
            <Field label="Szenarioname *">
              <input
                name="scenario_name"
                required
                maxLength={160}
                value={data.name}
                onChange={(e) => setData({ ...data, name: e.target.value })}
                placeholder="z. B. Geschäftsanwendung modernisieren"
              />
            </Field>
            <Field label="Branche *">
              <input
                required
                maxLength={120}
                value={data.company_profile.industry}
                onChange={(e) =>
                  setData({
                    ...data,
                    company_profile: { ...data.company_profile, industry: e.target.value },
                  })
                }
              />
            </Field>
            <Field label="Mitarbeitende">
              <input
                type="number"
                min="1"
                max="1000000"
                value={data.company_profile.employee_count ?? ''}
                onChange={(e) =>
                  setData({
                    ...data,
                    company_profile: {
                      ...data.company_profile,
                      employee_count: integer(e.target.value),
                    },
                  })
                }
                placeholder="Unbekannt"
              />
            </Field>
            <Field
              label="IT-Personal (Vollzeitäquivalente)"
              hint="Verfügbare interne IT-Kapazität, z. B. 1,5."
            >
              <input
                inputMode="decimal"
                pattern="[0-9]+([.,][0-9]+)?"
                value={data.company_profile.it_staff_fte ?? ''}
                onChange={(e) =>
                  setData({
                    ...data,
                    company_profile: {
                      ...data.company_profile,
                      it_staff_fte: decimal(e.target.value),
                    },
                  })
                }
                placeholder="Unbekannt"
              />
            </Field>
            <Field label="Monatliches Budget (EUR netto)">
              <input
                inputMode="decimal"
                pattern="[0-9]+([.,][0-9]+)?"
                value={data.company_profile.monthly_budget ?? ''}
                onChange={(e) =>
                  setData({
                    ...data,
                    company_profile: {
                      ...data.company_profile,
                      monthly_budget: decimal(e.target.value),
                    },
                  })
                }
                placeholder="Unbekannt"
              />
            </Field>
            <Field label="Einmaliges Budget (EUR netto)">
              <input
                inputMode="decimal"
                pattern="[0-9]+([.,][0-9]+)?"
                value={data.company_profile.initial_budget ?? ''}
                onChange={(e) =>
                  setData({
                    ...data,
                    company_profile: {
                      ...data.company_profile,
                      initial_budget: decimal(e.target.value),
                    },
                  })
                }
                placeholder="Unbekannt"
              />
            </Field>
            <Field
              label="Erforderliche Datenregion"
              hint="Der Demo-Katalog belegt EU-Betrieb. Andere Angaben werden gegen die Katalogevidenz geprüft."
            >
              <input
                required
                minLength={2}
                maxLength={64}
                value={data.requirements.region}
                onChange={(e) =>
                  setData({
                    ...data,
                    requirements: { ...data.requirements, region: e.target.value },
                  })
                }
              />
            </Field>
            <label className="check-field">
              <input
                type="checkbox"
                checked={data.requirements.hard_budget}
                onChange={(e) =>
                  setData({
                    ...data,
                    requirements: { ...data.requirements, hard_budget: e.target.checked },
                  })
                }
              />
              <span>
                Budget als harte Grenze anwenden
                <small>Überschreitungen schließen einen Plan aus.</small>
              </span>
            </label>
          </div>
          <p className="form-hint">
            * Pflichtfeld. Leere Zahlenfelder bedeuten „unbekannt“, niemals null Euro. Fehlende
            Fachangaben können eine bestätigte Empfehlung verhindern.
          </p>
        </fieldset>
        <section className="form-card">
          <div className="section-heading">
            <h2>
              <span className="step-number">02</span> Arbeitslasten{' '}
              <span className="count">{data.workloads.length}/10</span>
            </h2>
            <button
              type="button"
              className="secondary"
              disabled={pending || data.workloads.length >= 10}
              onClick={() => setData({ ...data, workloads: [...data.workloads, emptyWorkload()] })}
            >
              Arbeitslast hinzufügen
            </button>
          </div>
          {data.workloads.map((workload, index) => (
            <fieldset disabled={pending} className="workload-card" key={workload.workload_key}>
              <legend>
                Arbeitslast {index + 1}
                {workload.name && ' · ' + workload.name}
              </legend>
              <div className="form-grid">
                <Field label={'Name der Arbeitslast ' + (index + 1) + ' *'}>
                  <input
                    required
                    maxLength={160}
                    value={workload.name}
                    onChange={(e) => patchWorkload(index, { name: e.target.value })}
                  />
                </Field>
                <Field label="Art der Arbeitslast">
                  <select
                    value={workload.workload_type}
                    onChange={(e) =>
                      patchWorkload(index, {
                        workload_type: e.target.value as Workload['workload_type'],
                      })
                    }
                  >
                    {Object.entries(workloadTypes).map(([key, label]) => (
                      <option key={key} value={key}>
                        {label}
                      </option>
                    ))}
                  </select>
                </Field>
                <Field label="Nutzende">
                  <input
                    type="number"
                    min="1"
                    max="1000000"
                    value={workload.user_count ?? ''}
                    onChange={(e) => patchWorkload(index, { user_count: integer(e.target.value) })}
                    placeholder="Unbekannt"
                  />
                </Field>
                <Field label="Rechenleistung (vCPU)">
                  <input
                    inputMode="decimal"
                    pattern="[0-9]+([.,][0-9]+)?"
                    value={workload.vcpu_count ?? ''}
                    onChange={(e) => patchWorkload(index, { vcpu_count: decimal(e.target.value) })}
                    placeholder="Unbekannt"
                  />
                </Field>
                <Field label="Arbeitsspeicher (GiB)">
                  <input
                    inputMode="decimal"
                    pattern="[0-9]+([.,][0-9]+)?"
                    value={workload.memory_gib ?? ''}
                    onChange={(e) => patchWorkload(index, { memory_gib: decimal(e.target.value) })}
                    placeholder="Unbekannt"
                  />
                </Field>
                <Field label="Datenspeicher (GiB)">
                  <input
                    inputMode="decimal"
                    pattern="[0-9]+([.,][0-9]+)?"
                    value={workload.storage_gib ?? ''}
                    onChange={(e) => patchWorkload(index, { storage_gib: decimal(e.target.value) })}
                    placeholder="Unbekannt"
                  />
                </Field>
                <Field
                  label="Maximale Latenz (ms)"
                  hint="Höchste noch akzeptable Antwortverzögerung."
                >
                  <input
                    inputMode="decimal"
                    pattern="[0-9]+([.,][0-9]+)?"
                    value={workload.max_latency_ms ?? ''}
                    onChange={(e) =>
                      patchWorkload(index, { max_latency_ms: decimal(e.target.value) })
                    }
                    placeholder="Unbekannt"
                  />
                </Field>
                <Field label="Erforderliche Verfügbarkeit (%)">
                  <input
                    inputMode="decimal"
                    pattern="[0-9]+([.,][0-9]+)?"
                    value={workload.availability_percent ?? ''}
                    onChange={(e) =>
                      patchWorkload(index, { availability_percent: decimal(e.target.value) })
                    }
                    placeholder="Unbekannt"
                  />
                </Field>
                <Field
                  label="Wiederanlaufzeit / RTO (Sekunden)"
                  hint="Maximale Dauer bis zum Wiederanlauf."
                >
                  <input
                    type="number"
                    min="0"
                    max="31536000"
                    value={workload.rto_seconds ?? ''}
                    onChange={(e) => patchWorkload(index, { rto_seconds: integer(e.target.value) })}
                    placeholder="Unbekannt"
                  />
                </Field>
                <Field
                  label="Datenverlustfenster / RPO (Sekunden)"
                  hint="Maximal tolerierbares Alter des letzten Datenstands."
                >
                  <input
                    type="number"
                    min="0"
                    max="31536000"
                    value={workload.rpo_seconds ?? ''}
                    onChange={(e) => patchWorkload(index, { rpo_seconds: integer(e.target.value) })}
                    placeholder="Unbekannt"
                  />
                </Field>
                <Field label="Schutzbedarf">
                  <select
                    value={workload.sensitivity ?? ''}
                    onChange={(e) =>
                      patchWorkload(index, {
                        sensitivity: (e.target.value || null) as Workload['sensitivity'],
                      })
                    }
                  >
                    <option value="">Unbekannt</option>
                    {Object.entries(sensitivity).map(([key, label]) => (
                      <option key={key} value={key}>
                        {label}
                      </option>
                    ))}
                  </select>
                </Field>
                <Field label="Internetabhängigkeit zulässig?">
                  <select
                    value={
                      workload.internet_dependency_allowed === null
                        ? ''
                        : String(workload.internet_dependency_allowed)
                    }
                    onChange={(e) =>
                      patchWorkload(index, {
                        internet_dependency_allowed:
                          e.target.value === '' ? null : e.target.value === 'true',
                      })
                    }
                  >
                    <option value="">Unbekannt</option>
                    <option value="true">Ja</option>
                    <option value="false">Nein</option>
                  </select>
                </Field>
              </div>
              {data.workloads.length > 1 && (
                <button
                  className="text-button danger"
                  type="button"
                  onClick={() =>
                    setData({ ...data, workloads: data.workloads.filter((_, i) => i !== index) })
                  }
                >
                  Arbeitslast {index + 1} entfernen
                </button>
              )}
            </fieldset>
          ))}
        </section>
        <section className="form-card">
          <div className="section-heading">
            <div>
              <h2>
                <span className="step-number">03</span> Vorhandene IT-Assets
              </h2>
              <p className="muted">
                Optionales Inventar. Der M1-Katalog rechnet bestehende Assets nicht als
                Kostengutschrift an.
              </p>
            </div>
            <button
              className="secondary"
              type="button"
              disabled={pending || data.infrastructure_assets.length >= 100}
              onClick={() =>
                setData({
                  ...data,
                  infrastructure_assets: [
                    ...data.infrastructure_assets,
                    {
                      asset_key: 'asset_' + crypto.randomUUID().slice(0, 8),
                      name: '',
                      asset_type: 'SERVER',
                      quantity: 1,
                      notes: '',
                    },
                  ],
                })
              }
            >
              Asset hinzufügen
            </button>
          </div>
          {data.infrastructure_assets.length === 0 && (
            <p className="muted">Noch keine Assets erfasst.</p>
          )}
          {data.infrastructure_assets.map((asset, index) => (
            <fieldset className="workload-card" disabled={pending} key={asset.asset_key}>
              <legend>Asset {index + 1}</legend>
              <div className="form-grid">
                <Field label="Assetname *">
                  <input
                    required
                    maxLength={160}
                    value={asset.name}
                    onChange={(e) => patchAsset(index, { name: e.target.value })}
                  />
                </Field>
                <Field label="Assettyp">
                  <select
                    value={asset.asset_type}
                    onChange={(e) =>
                      patchAsset(index, { asset_type: e.target.value as Asset['asset_type'] })
                    }
                  >
                    {Object.entries(assetTypes).map(([key, label]) => (
                      <option key={key} value={key}>
                        {label}
                      </option>
                    ))}
                  </select>
                </Field>
                <Field label="Anzahl">
                  <input
                    type="number"
                    required
                    min="1"
                    max="1000000"
                    value={asset.quantity}
                    onChange={(e) => patchAsset(index, { quantity: Number(e.target.value) })}
                  />
                </Field>
                <Field label="Anmerkung">
                  <input
                    maxLength={2000}
                    value={asset.notes}
                    onChange={(e) => patchAsset(index, { notes: e.target.value })}
                  />
                </Field>
              </div>
              <button
                className="text-button danger"
                type="button"
                onClick={() =>
                  setData({
                    ...data,
                    infrastructure_assets: data.infrastructure_assets.filter((_, i) => i !== index),
                  })
                }
              >
                Asset {index + 1} entfernen
              </button>
            </fieldset>
          ))}
        </section>
        <ErrorNotice error={error} />
        <div className="form-actions">
          <p>
            {scenario
              ? 'Ausgangsversion ' + scenario.current_version
              : 'Erstellt die erste unveränderliche Profilversion.'}
          </p>
          <button type="button" className="secondary" onClick={onCancel} disabled={pending}>
            Abbrechen
          </button>
          <button type="submit" disabled={pending}>
            {pending
              ? 'Wird gespeichert …'
              : scenario
                ? 'Neue Version speichern'
                : 'Szenario speichern'}
          </button>
        </div>
      </form>
    </section>
  );
}
