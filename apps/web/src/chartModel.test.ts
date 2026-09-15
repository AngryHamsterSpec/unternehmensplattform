import { expect, it } from 'vitest';
import { frequencies, histogram, numericPoints, numericValue } from './chartModel';
import type { ChartSample, DataProfile } from './generated/domain';

it('macht Leerwerte, Nichtzahlen und nicht darstellbare Zahlen nicht zu Null', () => {
  for (const value of ['', ' ', 'NaN', 'Infinity', '0x10', '1e400', '1e-400', '9007199254740993']) {
    expect(numericValue(value)).toBeNull();
  }
  expect(numericValue('0')).toBe(0);
  expect(numericValue('-1.25')).toBe(-1.25);
  expect(numericValue('1e2')).toBe(100);
});
it('ordnet auch Maximum und konstante Zahlen genau einer Histogrammklasse zu', () => {
  expect(histogram([0, 1, 2, 3, 4], 2).map((v) => v.value)).toEqual([2, 3]);
  expect(histogram([7, 7, 7], 12)).toEqual([{ name: '7', value: 3 }]);
  expect(histogram([], 12)).toEqual([]);
});
it('ergänzt übrige und fehlende Werte zu einer vollständigen Ringverteilung', () => {
  const profile = {
    rows: 100,
    columns: [{ top_values: [{ value: 'Berlin', count: 40 }], missing: 10 }],
  } as DataProfile;
  const groups = frequencies(profile, 0);
  expect(groups.map((g) => g.value)).toEqual([40, 50, 10]);
  expect(groups.reduce((sum, g) => sum + g.value, 0)).toBe(100);
});
it('filtert Messwerte einschließlich Randwerten und lehnt verkehrte Grenzen ab', () => {
  const sample = {
    rows: [
      { row_number: 1, values: ['', '1'] },
      { row_number: 2, values: ['0', '2'] },
      { row_number: 3, values: ['5', ''] },
      { row_number: 4, values: ['10', '20'] },
    ],
  } as ChartSample;
  expect(numericPoints(sample, '0', '5').points.map((p) => p.row)).toEqual([2, 3]);
  expect(numericPoints(sample, '', '').excluded).toBe(1);
  expect(numericPoints(sample, '9', '1').invalid).toBe(true);
  expect(numericPoints(sample, 'abc', '').points).toEqual([]);
});
