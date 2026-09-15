import { test, expect } from '@playwright/test';
import type { Page } from '@playwright/test';

const password = process.env.DEMO_PASSWORD;
test.beforeAll(() => {
  if (!password) throw new Error('DEMO_PASSWORD für die synthetische OIDC-Demo fehlt.');
});

async function login(page: Page, username: string, organization: string) {
  await page.goto('/');
  await page.getByRole('link', { name: /Sicher anmelden/ }).click();
  await expect(page).toHaveURL(/identity\/realms\/platform/);
  await page.locator('#username').fill(username);
  await page.locator('#password').fill(password!);
  await page.locator('#kc-login').click();
  await expect(page.getByRole('heading', { name: 'Organisation auswählen' })).toBeVisible();
  await page.getByRole('button', { name: new RegExp(organization) }).click();
  await expect(
    page.getByRole('heading', { name: 'Unternehmensszenarien', exact: true }),
  ).toBeVisible();
}

test('OIDC, Profilversionen, Bewertung, Vergleich und Mandantenschutz', async ({ browser }) => {
  const contextA = await browser.newContext();
  const page = await contextA.newPage();
  const consoleErrors: string[] = [];
  page.on('pageerror', (error) => consoleErrors.push(error.message));
  await login(page, 'analyst', 'Musterwerk IT');
  const density = page.getByRole('button', { name: 'Kompakte Ansicht' });
  await density.click();
  await expect(density).toHaveAttribute('aria-pressed', 'true');
  await page.reload();
  await expect(page.getByRole('button', { name: 'Kompakte Ansicht' })).toHaveAttribute(
    'aria-pressed',
    'true',
  );
  await page.getByRole('button', { name: 'Kompakte Ansicht' }).click();
  await page
    .getByRole('searchbox', { name: 'Geladene Szenarien filtern' })
    .fill('nichtvorhanden-e2e-filter');
  await expect(page.getByText('Keine geladenen Szenarien passen zum Filter.')).toBeVisible();
  await page.getByRole('searchbox', { name: 'Geladene Szenarien filtern' }).fill('');

  await page.getByRole('button', { name: /Neues Szenario/ }).click();
  await page.getByRole('button', { name: 'Synthetisches Beispiel laden' }).click();
  await expect(page.getByLabel('Szenarioname *')).not.toHaveValue('');
  const unique = 'E2E Büro ' + Date.now();
  await page.getByLabel('Szenarioname *').fill(unique);
  await page.getByRole('button', { name: 'Szenario speichern' }).click();
  await expect(page.getByRole('heading', { name: unique, exact: true })).toBeVisible();
  const scenarioUrl = page.url();
  await page.reload();
  await expect(page.getByRole('heading', { name: unique, exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Bewertung starten' }).click();
  await expect(page.getByRole('heading', { name: 'Bewertung im Detail' })).toBeVisible();
  const resultUrl = page.url();
  await expect(page.getByText('Empfehlung im synthetischen Modell', { exact: true })).toBeVisible();
  await page.reload();
  await expect(page.getByRole('heading', { name: 'Bewertung im Detail' })).toBeVisible();
  await page.goto(scenarioUrl);
  await page.getByLabel('Bewertungsmodus').selectOption('PERFORMANCE');
  await page.getByRole('button', { name: 'Bewertung starten' }).click();
  await expect(page.getByRole('heading', { name: 'Bewertung im Detail' })).toBeVisible();
  await page.getByRole('link', { name: 'Vergleich', exact: true }).click();
  const boxes = page.getByRole('checkbox', { name: /Bewertung auswählen/ });
  await boxes.nth(0).check();
  await boxes.nth(1).check();
  await page.getByRole('button', { name: /Auswahl vergleichen/ }).click();
  await expect(
    page.getByRole('heading', { name: 'Vergleich der gespeicherten Ergebnisse' }),
  ).toBeVisible();
  await page.goto(scenarioUrl);
  await page.getByRole('button', { name: 'Szenario bearbeiten' }).click();
  await page.getByLabel('Arbeitsspeicher (GiB)').fill('');
  await page.getByRole('button', { name: 'Neue Version speichern' }).click();
  await page.getByRole('button', { name: 'Bewertung starten' }).click();
  await expect(page.getByText('Keine bestätigte Empfehlung', { exact: true })).toBeVisible();
  await page.goto(resultUrl);
  await expect(page.getByText('Empfehlung im synthetischen Modell', { exact: true })).toBeVisible();

  const contextB = await browser.newContext();
  const other = await contextB.newPage();
  await login(other, 'mandant-b', 'Testmandant B');
  await other.goto(resultUrl);
  await expect(other.getByRole('alert')).toContainText('Bewertung nicht gefunden');
  await other.goto(scenarioUrl);
  await expect(other.getByRole('alert')).toContainText('Szenario nicht gefunden');
  await contextB.close();

  await page.getByRole('button', { name: 'Abmelden', exact: true }).click();
  await expect(page.getByRole('link', { name: /Sicher anmelden/ })).toBeVisible();
  await page.goto(resultUrl);
  await expect(page.getByRole('link', { name: /Sicher anmelden/ })).toBeVisible();
  expect(consoleErrors).toEqual([]);
  await contextA.close();
});

test('Lesekonto sieht Inhalte, aber keine Schreib- oder Administrationsaktionen', async ({
  browser,
}) => {
  const context = await browser.newContext();
  const page = await context.newPage();
  await login(page, 'viewer', 'Musterwerk IT');
  await expect(page.getByRole('button', { name: /Neues Szenario/ })).toHaveCount(0);
  await expect(page.getByRole('link', { name: 'Mitglieder & Rechte' })).toHaveCount(0);
  await expect(page.getByRole('link', { name: 'Audit-Protokoll' })).toHaveCount(0);
  await context.close();
});

test('Gespeicherter Text bleibt inert; Header, Tastatur und schmale Ansicht', async ({
  browser,
}) => {
  const context = await browser.newContext({ viewport: { width: 390, height: 844 } });
  const page = await context.newPage();
  const external: string[] = [];
  const dialogs: string[] = [];
  page.on('request', (request) => {
    if (request.url().includes('example.invalid')) external.push(request.url());
  });
  page.on('dialog', async (dialog) => {
    dialogs.push(dialog.message());
    await dialog.dismiss();
  });
  await login(page, 'analyst', 'Musterwerk IT');
  const navigation = page.getByRole('button', { name: 'Navigation', exact: true });
  await expect(navigation).toHaveAttribute('aria-expanded', 'false');
  await navigation.click();
  await expect(page.getByRole('link', { name: 'Datenwerkstatt', exact: true })).toBeVisible();
  await page.getByRole('link', { name: 'Datenwerkstatt', exact: true }).press('Escape');
  await expect(navigation).toBeFocused();
  await expect(navigation).toHaveAttribute('aria-expanded', 'false');
  await navigation.click();
  await page.getByRole('link', { name: 'Szenarien', exact: true }).click();
  await expect(navigation).toHaveAttribute('aria-expanded', 'false');
  const home = await page.request.get('/');
  expect(home.headers()['content-security-policy']).toContain("script-src 'self'");
  expect(home.headers()['x-frame-options']).toBe('DENY');
  expect(home.headers()['x-content-type-options']).toBe('nosniff');
  expect((await page.request.get('/identity/admin/')).status()).toBe(404);
  const api = await page.request.get('/api/v1/scenarios?limit=1');
  expect(api.headers()['cache-control']).toContain('no-store');
  await page.getByRole('button', { name: /Neues Szenario/ }).click();
  await page.getByRole('button', { name: 'Synthetisches Beispiel laden' }).click();
  await expect(page.getByLabel('Szenarioname *')).not.toHaveValue('');
  const payload = '<img src="https://example.invalid/xss" onerror="alert(1)"> ' + Date.now();
  await page.getByLabel('Szenarioname *').fill(payload);
  await page.getByRole('button', { name: 'Szenario speichern' }).click();
  await expect(page.getByRole('heading', { name: payload, exact: true })).toBeVisible();
  await page.reload();
  await expect(page.getByRole('heading', { name: payload, exact: true })).toBeVisible();
  expect(await page.locator('main img').count()).toBe(0);
  expect(external).toEqual([]);
  expect(dialogs).toEqual([]);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(
    true,
  );
  await page.screenshot({ path: 'test-results/design-mobile.png', fullPage: true });
  await page.keyboard.press('Tab');
  await expect(page.getByRole('link', { name: 'Zum Inhalt springen' })).toBeFocused();
  await page.keyboard.press('Enter');
  await expect(page.locator('#main-content')).toBeFocused();
  await page.getByRole('button', { name: 'Bewertung starten' }).click();
  await expect(page.getByRole('heading', { name: 'Bewertung im Detail' })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(
    true,
  );
  await context.close();
});

// Dieser zusätzliche Fall wird ausschließlich vom vollständigen Restorelauf
// mit einem vor dem Backup gespeicherten Ergebnis aktiviert.
if (process.env.RESTORE_ASSESSMENT_ID || process.env.RESTORE_ASSESSMENT_HASH) {
  test('Wiederhergestellte Identität öffnet historische Bewertung mit identischem Hash', async ({
    browser,
  }) => {
    const id = process.env.RESTORE_ASSESSMENT_ID;
    const hash = process.env.RESTORE_ASSESSMENT_HASH;
    expect(id).toMatch(/^[0-9a-f-]{36}$/);
    expect(hash).toMatch(/^[0-9a-f]{64}$/);
    const context = await browser.newContext();
    const page = await context.newPage();
    await login(page, 'analyst', 'Musterwerk IT');
    await page.goto('/#/bewertung/' + id);
    await expect(page.getByRole('heading', { name: 'Bewertung im Detail' })).toBeVisible();
    await expect(page.getByText(hash!, { exact: true })).toBeVisible();
    await expect(
      page.getByText('Empfehlung im synthetischen Modell', { exact: true }),
    ).toBeVisible();
    await page.reload();
    await expect(page.getByText(hash!, { exact: true })).toBeVisible();
    const datasetId = process.env.RESTORE_DATASET_ID;
    const dataHash = process.env.RESTORE_DATA_HASH;
    expect(datasetId).toMatch(/^[0-9a-f-]{36}$/);
    expect(dataHash).toMatch(/^[0-9a-f]{64}$/);
    await page.goto('/#/daten/' + datasetId);
    await expect(page.getByLabel('Datenversion')).toBeVisible();
    await page.getByLabel('Datenversion').selectOption('2');
    await page.getByText('Metadaten und Prüfsumme', { exact: true }).click();
    await expect(page.getByText('Daten-SHA-256: ' + dataHash, { exact: true })).toBeVisible();
    await page.reload();
    await expect(page.getByLabel('Datenversion')).toBeVisible();
    await page.getByLabel('Datenversion').selectOption('2');
    await page.getByText('Metadaten und Prüfsumme', { exact: true }).click();
    await expect(page.getByText('Daten-SHA-256: ' + dataHash, { exact: true })).toBeVisible();
    const analysisId = process.env.RESTORE_ANALYSIS_ID;
    const analysisHash = process.env.RESTORE_ANALYSIS_HASH;
    expect(analysisId).toMatch(/^[0-9a-f-]{36}$/);
    expect(analysisHash).toMatch(/^[0-9a-f]{64}$/);
    await page.goto('/#/daten/' + process.env.RESTORE_ANALYSIS_DATASET_ID);
    const quality = page.locator('#dataset-quality');
    await expect(
      quality.getByRole('heading', {
        name: 'Analysebericht · Version ' + process.env.RESTORE_ANALYSIS_VERSION,
      }),
    ).toBeVisible();
    const restoredReport = await page.request.get(
      '/api/v1/data-tasks/' + analysisId + '/report?format=json',
    );
    expect(restoredReport.status()).toBe(200);
    expect((await restoredReport.json()).result_hash).toBe(analysisHash);
    await page.reload();
    await expect(
      quality.getByRole('heading', {
        name: 'Analysebericht · Version ' + process.env.RESTORE_ANALYSIS_VERSION,
      }),
    ).toBeVisible();
    await context.close();
  });
}

test('CSV-Import, Vorschau, bestätigte Version, Export und Rechte', async ({ browser }) => {
  const context = await browser.newContext();
  const page = await context.newPage();
  const errors: string[] = [];
  page.on('pageerror', (error) => errors.push(error.message));
  await login(page, 'analyst', 'Musterwerk IT');
  await page.getByRole('link', { name: 'Datenwerkstatt', exact: true }).click();
  await page.getByRole('button', { name: 'Datei importieren', exact: true }).click();
  await page.getByRole('button', { name: 'Synthetische CSV laden' }).click();
  const name = 'E2E CSV ' + Date.now();
  await page.getByLabel('Datensatzname').fill(name);
  await page.getByRole('button', { name: 'CSV importieren', exact: true }).click();
  await expect(page.getByRole('heading', { name, exact: true })).toBeVisible();
  await expect(page.getByLabel('Datenversion')).toHaveValue('1', { timeout: 30000 });
  const url = page.url();
  const did = new URL(url).hash.split('/')[2];
  const charts = page.getByRole('region', { name: 'Visuelle Datenanalyse' });
  await expect(charts.getByRole('heading', { name: 'Visuelle Analyse' })).toBeVisible();
  await expect(charts.getByTestId('data-chart').locator('svg')).toBeVisible();
  await charts.getByRole('button', { name: 'Ring', exact: false }).click();
  await expect(charts.getByRole('button', { name: 'Ring', exact: false })).toHaveAttribute(
    'aria-pressed',
    'true',
  );
  const svgDownload = page.waitForEvent('download');
  await charts.getByRole('button', { name: 'SVG exportieren' }).click();
  const svgFile = await svgDownload;
  expect(svgFile.suggestedFilename()).toBe('diagramm-v1-donut.svg');
  const svgStream = await svgFile.createReadStream();
  const svgChunks: Buffer[] = [];
  for await (const chunk of svgStream!) svgChunks.push(Buffer.from(chunk));
  const svg = Buffer.concat(svgChunks).toString('utf8');
  expect(svg).toContain('<svg');
  expect(svg).toContain('Version 1');
  expect(svg).not.toMatch(/<script|onerror=/);
  await charts.getByRole('button', { name: 'Histogramm', exact: false }).click();
  await expect(charts.getByText(/Alle 5 von 5 Zeilen/).first()).toBeVisible();
  await charts.getByLabel('Messwert ab', { exact: false }).fill('100');
  await charts.getByLabel('Messwert bis', { exact: false }).fill('200');
  await expect(charts.getByText(/sichtbar: 2/).first()).toBeVisible();
  await charts.getByLabel('Messwert bis', { exact: false }).fill('50');
  await expect(charts.getByRole('alert')).toContainText('Untergrenze');
  await charts.getByRole('button', { name: 'Filter zurücksetzen' }).click();
  await charts.getByRole('button', { name: 'Streudiagramm', exact: false }).click();
  await expect(charts.getByLabel('Y-Achse')).toBeVisible();
  await charts.getByRole('button', { name: 'Linie', exact: false }).click();
  await expect(charts.getByText(/keine Zeitreihe/)).toBeVisible();
  await charts.getByLabel('Darstellung', { exact: true }).selectOption('static');
  await expect(charts.getByRole('button', { name: 'Zoom zurücksetzen' })).toHaveCount(0);
  const pngDownload = page.waitForEvent('download');
  await charts.getByRole('button', { name: 'PNG exportieren' }).click();
  const pngFile = await pngDownload;
  const pngStream = await pngFile.createReadStream();
  const pngChunks: Buffer[] = [];
  for await (const chunk of pngStream!) pngChunks.push(Buffer.from(chunk));
  expect(Buffer.concat(pngChunks).subarray(0, 8).toString('hex')).toBe('89504e470d0a1a0a');
  await charts.getByRole('button', { name: 'Datenqualität', exact: false }).click();
  await charts.getByRole('button', { name: 'Ansicht vergrößern' }).click();
  await expect(charts.getByRole('button', { name: 'Ansicht verkleinern' })).toBeVisible();
  await charts.getByRole('button', { name: 'Ansicht verkleinern' }).click();
  await page.setViewportSize({ width: 390, height: 844 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(
    true,
  );
  await page.setViewportSize({ width: 1280, height: 900 });

  await page.getByText('Herkunft und Originaldatei', { exact: true }).click();
  const originalHash = await page.getByText(/^Original-SHA-256:/).textContent();
  await page.getByRole('button', { name: 'Schritt hinzufügen', exact: true }).click();
  await page.getByLabel('Bereinigungsschritt').selectOption('drop_empty_rows');
  await page.getByRole('button', { name: 'Schritt hinzufügen', exact: true }).click();
  await page.getByLabel('Bereinigungsschritt').selectOption('drop_duplicates');
  await page.getByRole('button', { name: 'Schritt hinzufügen', exact: true }).click();
  await page.getByRole('button', { name: 'Vorschau berechnen', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Vorschau · noch nicht übernommen' })).toBeVisible(
    { timeout: 30000 },
  );
  await expect(page.getByLabel('Datenversion')).toHaveValue('1');
  await expect(page.getByText('Zeilen: 5 → 3', { exact: false })).toBeVisible();
  await page.reload();
  await expect(page.getByLabel('Gespeicherte Vorschau erneut öffnen')).toBeVisible();
  await page.getByLabel('Gespeicherte Vorschau erneut öffnen').selectOption({ index: 1 });
  await expect(
    page.getByRole('heading', { name: 'Vorschau · noch nicht übernommen' }),
  ).toBeVisible();
  await expect(page.getByText('Zeilen: 5 → 3', { exact: false })).toBeVisible();
  await page.getByRole('button', { name: 'Vorschau bestätigen und Version 2 speichern' }).click();
  await expect(page.getByLabel('Datenversion')).toHaveValue('2');
  await page.reload();
  await expect(page.getByLabel('Datenversion')).toHaveValue('2');
  await page.getByText('Herkunft und Originaldatei', { exact: true }).click();
  await expect(page.getByText(/^Original-SHA-256:/)).toHaveText(originalHash!);
  await page.getByLabel('Datenversion').selectOption('1');
  await expect(page.getByRole('button', { name: 'Version 1 als CSV exportieren' })).toBeVisible();
  await page.getByLabel('Datenversion').selectOption('2');
  const download = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Version 2 als CSV exportieren' }).click();
  expect((await download).suggestedFilename()).toContain('-v2.csv');
  await expect(page.getByText(/CSV-Download gestartet. Geschützte Zellen: 0/)).toBeVisible();
  const exported = await page.request.get('/api/v1/datasets/' + did + '/versions/2/export');
  expect(exported.status()).toBe(200);
  expect(await exported.text()).toContain('"Anna";"Vertrieb"');
  await page.setViewportSize({ width: 390, height: 844 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(
    true,
  );
  expect(errors).toEqual([]);

  const viewerContext = await browser.newContext();
  const viewer = await viewerContext.newPage();
  await login(viewer, 'viewer', 'Musterwerk IT');
  await viewer.goto(url);
  await expect(viewer.getByLabel('Datenversion')).toHaveValue('2');
  await expect(viewer.getByRole('heading', { name: 'Bereinigung planen' })).toHaveCount(0);
  const otherContext = await browser.newContext();
  const other = await otherContext.newPage();
  await login(other, 'mandant-b', 'Testmandant B');
  await other.goto(url);
  await expect(other.getByRole('alert')).toContainText('Datensatz wurde nicht gefunden');
  expect((await other.request.get('/api/v1/datasets/' + did + '/versions/2/export')).status()).toBe(
    404,
  );
  await Promise.all([context.close(), viewerContext.close(), otherContext.close()]);
});

test('CSV über 128 KiB: abschnittsweiser Browserimport und vollständiges Profil', async ({
  page,
}) => {
  await login(page, 'analyst', 'Musterwerk IT');
  await page.getByRole('link', { name: 'Datenwerkstatt', exact: true }).click();
  await page.getByRole('button', { name: 'Datei importieren', exact: true }).click();
  const name = 'Große synthetische CSV ' + Date.now();
  await page.getByLabel('Datensatzname').fill(name);
  test.setTimeout(120000);
  const content = Buffer.from('Name;Betrag\n' + 'Anna;1.25\n'.repeat(450000));
  expect(content.length).toBeGreaterThan(2088432);
  const sizes: number[] = [];
  page.on('response', async (response) => {
    if (response.url().includes('/chunks/') && response.ok()) {
      sizes.push(((await response.json()) as { received_bytes: number }).received_bytes);
    }
  });
  await page
    .getByLabel('Datendatei')
    .setInputFiles({ name: 'gross-synthetisch.csv', mimeType: 'text/csv', buffer: content });
  await expect(page.getByText(/bis 1 GiB/)).toBeVisible();
  await page.getByRole('button', { name: 'CSV importieren', exact: true }).click();
  await expect(page.getByRole('heading', { name, exact: true })).toBeVisible();
  await expect(page.getByLabel('Datenqualität')).toContainText('450.000', { timeout: 120000 });
  expect(sizes.length).toBe(2);
  expect(sizes.at(-1)).toBe(content.length);
  expect(
    sizes.every(
      (size, i) => size - (sizes[i - 1] ?? 0) > 0 && size - (sizes[i - 1] ?? 0) <= 4194304,
    ),
  ).toBeTruthy();
  await page.getByText('Metadaten und Prüfsumme', { exact: true }).click();
  await expect(page.getByText('csv-profile-stream-2', { exact: false })).toBeVisible();
  await page.getByRole('button', { name: 'Letzte Zeilen', exact: true }).click();
  await expect(page.getByText('449.976–450.000 von 450.000')).toBeVisible();
});

test('CSV-Formaterkennung und Wiederaufnahme mit langem Textfeld', async ({ browser }) => {
  const context = await browser.newContext();
  const page = await context.newPage();
  await login(page, 'mandant-b', 'Testmandant B');
  await page.getByRole('link', { name: 'Datenwerkstatt', exact: true }).click();
  await page.getByRole('button', { name: 'Datei importieren', exact: true }).click();
  await page.getByLabel('Datensatzname').fill('E2E CSV Wiederaufnahme ' + Date.now());
  const content = Buffer.from('A,B\n1,' + 'x'.repeat(175026) + '\n', 'utf8');
  await page.getByLabel('Datendatei', { exact: true }).setInputFiles({
    name: 'synthetisch-langes-textfeld.csv',
    mimeType: 'text/csv',
    buffer: content,
  });
  await page.getByLabel('Trennzeichen', { exact: true }).selectOption(';');
  await page.getByRole('button', { name: 'CSV importieren', exact: true }).click();
  await expect(
    page.getByRole('heading', { name: 'Import aus Originaldatei wiederholen' }),
  ).toBeVisible({ timeout: 60000 });
  await expect(page.getByText(/wahrscheinlich Komma/)).toBeVisible();
  await expect(page.getByLabel('Trennzeichen', { exact: true })).toHaveValue('auto');
  await page.getByRole('button', { name: 'Gespeicherte Datei erneut importieren' }).click();
  await expect(page.getByLabel('Datenversion')).toHaveValue('1', { timeout: 60000 });
  await expect(
    page.getByRole('heading', { name: 'Import aus Originaldatei wiederholen' }),
  ).toHaveCount(0);
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.screenshot({ path: 'test-results/design-data.png', fullPage: true });
  const did = new URL(page.url()).hash.split('/')[2];
  const original = await page.request.get('/api/v1/datasets/' + did + '/original');
  expect(await original.body()).toEqual(content);
  await page.getByRole('button', { name: 'Schritt hinzufügen', exact: true }).click();
  await page.getByRole('button', { name: 'Vorschau berechnen', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Vorschau · noch nicht übernommen' })).toBeVisible(
    { timeout: 60000 },
  );
  await page.getByRole('button', { name: 'Vorschau bestätigen und Version 2 speichern' }).click();
  await expect(page.getByLabel('Datenversion')).toHaveValue('2');
  const exported = await page.request.get('/api/v1/datasets/' + did + '/versions/2/export');
  expect(exported.status()).toBe(200);
  expect(await exported.text()).toContain('x'.repeat(175026));

  await page.getByRole('link', { name: 'Datenwerkstatt', exact: true }).click();
  await page.getByRole('button', { name: 'Datei importieren', exact: true }).click();
  await page.getByLabel('Datensatzname').fill('E2E JSON ' + Date.now());
  const jsonContent = Buffer.from('[{"Name":" Anna ","Wert":1.25},{"Name":"Bob","Wert":null}]');
  await page.getByLabel('Datendatei', { exact: true }).setInputFiles({
    name: 'synthetisch.json',
    mimeType: 'application/json',
    buffer: jsonContent,
  });
  await expect(page.getByLabel('Trennzeichen', { exact: true })).toHaveCount(0);
  await page.getByRole('button', { name: 'JSON importieren', exact: true }).click();
  await expect(page.getByLabel('Datenversion')).toHaveValue('1', { timeout: 30000 });
  await expect(page.getByText(/Quelle: JSON/)).toBeVisible();
  const jsonDid = new URL(page.url()).hash.split('/')[2];
  expect(
    await (await page.request.get('/api/v1/datasets/' + jsonDid + '/original')).body(),
  ).toEqual(jsonContent);
  await page.getByRole('button', { name: 'Schritt hinzufügen', exact: true }).click();
  await page.getByRole('button', { name: 'Vorschau berechnen', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Vorschau · noch nicht übernommen' })).toBeVisible(
    { timeout: 30000 },
  );
  await page.getByRole('button', { name: 'Vorschau bestätigen und Version 2 speichern' }).click();
  await expect(page.getByLabel('Datenversion')).toHaveValue('2');
  expect(
    await (await page.request.get('/api/v1/datasets/' + jsonDid + '/versions/2/export')).text(),
  ).toContain('"Anna";"1.25"');

  await page.getByRole('link', { name: 'Datenwerkstatt', exact: true }).click();
  await page.getByRole('button', { name: 'Datei importieren', exact: true }).click();
  await page.getByLabel('Datensatzname').fill('E2E XLSX ' + Date.now());
  await page
    .getByLabel('Datendatei', { exact: true })
    .setInputFiles('e2e/fixtures/synthetisch.xlsx');
  await page.getByLabel('Arbeitsblatt (Nummer)').fill('2');
  await expect(page.getByLabel('Trennzeichen', { exact: true })).toHaveCount(0);
  await page.getByRole('button', { name: 'Excel importieren', exact: true }).click();
  await expect(page.getByLabel('Datenversion')).toHaveValue('1', { timeout: 30000 });
  await expect(page.getByText(/Quelle: XLSX · Arbeitsblatt 2/)).toBeVisible();
  await page.getByRole('button', { name: 'Schritt hinzufügen', exact: true }).click();
  await page.getByRole('button', { name: 'Vorschau berechnen', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Vorschau · noch nicht übernommen' })).toBeVisible(
    { timeout: 30000 },
  );
  await page.getByRole('button', { name: 'Vorschau bestätigen und Version 2 speichern' }).click();
  await expect(page.getByLabel('Datenversion')).toHaveValue('2');
  await expect(page.getByText(/Quelle: XLSX · Arbeitsblatt 2/)).toBeVisible();
  const excelDid = new URL(page.url()).hash.split('/')[2];
  expect(
    await (await page.request.get('/api/v1/datasets/' + excelDid + '/versions/2/export')).text(),
  ).toContain('"Anna";"1.25"');
  await context.close();
});

test('SQLite-Snapshot, Tabellenkorrektur, Bereinigung und Originalschutz', async ({ browser }) => {
  const context = await browser.newContext();
  const page = await context.newPage();
  await login(page, 'mandant-b', 'Testmandant B');
  await page.getByRole('link', { name: 'Datenwerkstatt', exact: true }).click();
  await page.getByRole('button', { name: 'Datei importieren', exact: true }).click();
  await page.getByLabel('Datensatzname').fill('E2E SQLite ' + Date.now());
  await page
    .getByLabel('Datendatei', { exact: true })
    .setInputFiles('e2e/fixtures/synthetisch.sqlite');
  await expect(page.getByLabel('SQLite-Tabelle')).toBeVisible();
  await expect(page.getByLabel('Trennzeichen', { exact: true })).toHaveCount(0);
  await page.getByRole('button', { name: 'SQLite importieren', exact: true }).click();
  await expect(page.getByText(/Bitte einen vorhandenen SQLite-Tabellennamen/)).toBeVisible({
    timeout: 30000,
  });
  await page.getByLabel('SQLite-Tabelle').fill('Daten');
  await page.getByRole('button', { name: 'Gespeicherte Datei erneut importieren' }).click();
  await expect(page.getByLabel('Datenversion')).toHaveValue('1', { timeout: 30000 });
  await expect(page.getByText(/Quelle: SQLite · Tabelle Daten/)).toBeVisible();
  const did = new URL(page.url()).hash.split('/')[2];
  const original = await (await page.request.get('/api/v1/datasets/' + did + '/original')).body();
  expect(original.subarray(0, 15).toString()).toBe('SQLite format 3');
  await page.getByRole('button', { name: 'Bereinigung', exact: true }).click();
  await page.getByRole('button', { name: 'Schritt hinzufügen', exact: true }).click();
  await page.getByRole('button', { name: 'Vorschau berechnen', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Vorschau · noch nicht übernommen' })).toBeVisible(
    { timeout: 30000 },
  );
  await page.getByRole('button', { name: 'Vorschau bestätigen und Version 2 speichern' }).click();
  await expect(page.getByLabel('Datenversion')).toHaveValue('2');
  await expect(page.getByText(/Quelle: SQLite · Tabelle Daten/)).toBeVisible();
  expect(
    await (await page.request.get('/api/v1/datasets/' + did + '/versions/2/export')).text(),
  ).toContain('"Anna";"1.25"');
  expect(await (await page.request.get('/api/v1/datasets/' + did + '/original')).body()).toEqual(
    original,
  );
  await context.close();
});

test('Parquet-Import, Bereinigung, Version und unverändertes Original', async ({ browser }) => {
  const context = await browser.newContext();
  const page = await context.newPage();
  await login(page, 'mandant-b', 'Testmandant B');
  await page.getByRole('link', { name: 'Datenwerkstatt', exact: true }).click();
  await page.getByRole('button', { name: 'Datei importieren', exact: true }).click();
  await page.getByLabel('Datensatzname').fill('E2E Parquet ' + Date.now());
  await page
    .getByLabel('Datendatei', { exact: true })
    .setInputFiles('e2e/fixtures/synthetisch.parquet');
  await expect(page.getByLabel('Trennzeichen', { exact: true })).toHaveCount(0);
  await expect(page.getByLabel('Arbeitsblatt (Nummer)')).toHaveCount(0);
  await page.getByRole('button', { name: 'Parquet importieren', exact: true }).click();
  await expect(page.getByLabel('Datenversion')).toHaveValue('1', { timeout: 30000 });
  await expect(page.getByText(/Quelle: Parquet/)).toBeVisible();
  const did = new URL(page.url()).hash.split('/')[2];
  const original = await (await page.request.get('/api/v1/datasets/' + did + '/original')).body();
  expect(original.subarray(0, 4).toString()).toBe('PAR1');
  await page.getByRole('button', { name: 'Bereinigung', exact: true }).click();
  await expect(page.locator('#dataset-cleaning')).toBeFocused();
  await page.getByRole('button', { name: 'Schritt hinzufügen', exact: true }).click();
  await page.getByRole('button', { name: 'Vorschau berechnen', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Vorschau · noch nicht übernommen' })).toBeVisible(
    { timeout: 30000 },
  );
  await page.getByRole('button', { name: 'Vorschau bestätigen und Version 2 speichern' }).click();
  await expect(page.getByLabel('Datenversion')).toHaveValue('2');
  await expect(page.getByText(/Quelle: Parquet/)).toBeVisible();
  expect(
    await (await page.request.get('/api/v1/datasets/' + did + '/versions/2/export')).text(),
  ).toContain('"Anna";"1.25"');
  expect(await (await page.request.get('/api/v1/datasets/' + did + '/original')).body()).toEqual(
    original,
  );
  await context.close();
});
