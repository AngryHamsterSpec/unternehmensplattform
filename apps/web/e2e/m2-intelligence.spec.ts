import { test, expect } from '@playwright/test';

test('M2 Vollablauf mit PostgreSQL, Qualitätsregeln, Analysebericht und geprüftem Plan', async ({
  page,
}) => {
  const errors: string[] = [];
  page.on('pageerror', (error) => errors.push(error.message));
  await page.goto('/');
  await page.getByRole('link', { name: /Sicher anmelden/ }).click();
  await page.locator('#username').fill('analyst');
  await page.locator('#password').fill(process.env.DEMO_PASSWORD!);
  await page.locator('#kc-login').click();
  await page.getByRole('button', { name: /Musterwerk IT/ }).click();
  await expect(
    page.getByRole('heading', { name: 'Unternehmensszenarien', exact: true }),
  ).toBeVisible();
  await page.getByRole('link', { name: 'Datenwerkstatt', exact: true }).click();
  await page.getByText('Datenbankquelle importieren', { exact: true }).click();
  await page
    .getByRole('combobox', { name: 'Datenbankquelle', exact: true })
    .selectOption('synthetischer-vertrieb');
  const name = 'M2 Quellenworkflow ' + Date.now();
  await page.getByLabel('Name des Datenbanksnapshots').fill(name);
  await page.getByRole('button', { name: 'Datenbanksnapshot importieren' }).click();
  await page.getByRole('button', { name: 'Importierten Datensatz öffnen' }).click();
  await expect(page.getByRole('heading', { name, exact: true })).toBeVisible();
  await expect(page.getByRole('combobox', { name: 'Datenversion', exact: true })).toHaveValue('1');
  const original = await page.request.get(
    '/api/v1/datasets/' + page.url().split('/').pop() + '/original',
  );
  const bytes = await original.body();
  expect(bytes.toString()).not.toContain('RLS-ausgeschlossen');
  const quality = page.locator('#dataset-quality');
  await quality.getByText('Analyse konfigurieren', { exact: true }).click();
  await quality.getByRole('combobox', { name: 'Zeitspalte', exact: true }).selectOption('datum');
  await quality.getByLabel('Zeitreihen-Kennzahl').selectOption('umsatz');
  await quality.getByLabel('Regelspalte').selectOption('umsatz');
  await quality
    .getByRole('combobox', { name: 'Qualitätsregel', exact: true })
    .selectOption('range');
  await quality.getByLabel('Untergrenze').fill('0');
  await quality.getByLabel('Obergrenze').fill('1000');
  await quality.getByRole('button', { name: 'Qualitätsregel hinzufügen' }).click();
  await quality.getByLabel('Name des Regelsatzes').fill('M2 Betragsgrenzen ' + Date.now());
  await quality.getByRole('button', { name: 'Regelsatz als neue Version speichern' }).click();
  await expect(quality.getByLabel('Qualitätsregelsatz')).not.toHaveValue('');
  await quality.getByRole('button', { name: 'Vollanalyse starten' }).click();
  await expect(quality.getByRole('heading', { name: 'Analysebericht · Version 1' })).toBeVisible();
  await expect(quality.getByRole('table', { name: 'Fachliche Qualitätsregeln' })).toContainText(
    'umsatz',
  );
  await quality.getByLabel('Analysevisualisierung').selectOption('correlation');
  await expect(quality.locator('svg').first()).toBeVisible();
  await quality.getByLabel('Analysevisualisierung').selectOption('time');
  await quality.getByLabel('Zeitverlaufswert').selectOption('sum');
  await quality
    .getByRole('combobox', { name: 'Diagramm-Modus', exact: true })
    .selectOption('static');
  const svgDownload = page.waitForEvent('download');
  await quality.getByRole('button', { name: 'Analysediagramm als SVG' }).click();
  expect((await svgDownload).suggestedFilename()).toMatch(/\.svg$/);
  const download = page.waitForEvent('download');
  await quality.getByRole('button', { name: 'Analysebericht herunterladen' }).click();
  expect((await download).suggestedFilename()).toMatch(/\.html$/);
  await quality.screenshot({ path: 'test-results/m2-vollanalyse.png' });
  await page.reload();
  await expect(page.getByRole('heading', { name: 'Analysebericht · Version 1' })).toBeVisible();
  await page.getByText('Assistierte Bereinigungsplanung', { exact: true }).click();
  await page.getByRole('button', { name: 'Bereinigungsplan erstellen' }).click();
  await expect(page.getByRole('heading', { name: 'Regelbasiert erstellter Plan' })).toBeVisible();
  await page.getByRole('button', { name: 'Geprüften Plan als Vorschau berechnen' }).click();
  await expect(
    page.getByRole('heading', { name: 'Vorschau · noch nicht übernommen' }),
  ).toBeVisible();
  await expect(page.getByRole('combobox', { name: 'Datenversion', exact: true })).toHaveValue('1');
  await page.getByRole('button', { name: 'Vorschau bestätigen und Version 2 speichern' }).click();
  await expect(page.getByRole('combobox', { name: 'Datenversion', exact: true })).toHaveValue('2');
  const finalOriginal = await page.request.get(
    '/api/v1/datasets/' + page.url().split('/').pop() + '/original',
  );
  expect(await finalOriginal.body()).toEqual(bytes);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({ path: 'test-results/m2-mobil.png', fullPage: true });
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1),
  ).toBe(true);
  expect(errors).toEqual([]);
});
