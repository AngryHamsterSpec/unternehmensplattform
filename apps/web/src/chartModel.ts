import type { ChartSample, DataProfile } from './generated/domain';

export type ChartKind = 'bar' | 'donut' | 'quality' | 'histogram' | 'line' | 'scatter';
export const chartNames: Record<ChartKind, string> = {
  bar: 'Balken',
  donut: 'Ring',
  quality: 'Datenqualität',
  histogram: 'Histogramm',
  line: 'Linie',
  scatter: 'Streudiagramm',
};
export const numericValue = (value: string): number | null => {
  const clean = value.trim();
  if (!/^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$/.test(clean)) return null;
  const number = Number(clean);
  if (!Number.isFinite(number) || Math.abs(number) > Number.MAX_SAFE_INTEGER) return null;
  if (number === 0 && /[1-9]/.test(clean.split(/[eE]/)[0])) return null;
  return number;
};
export const numberLabel = (n: number) =>
  new Intl.NumberFormat('de-DE', {
    maximumSignificantDigits: 5,
  }).format(n);
export const shortLabel = (text: string, max = 34) =>
  text.length > max ? text.slice(0, max - 1) + '…' : text;

export function frequencies(profile: DataProfile, columnIndex: number) {
  const column = profile.columns[columnIndex];
  if (!column) return [];
  const values = column.top_values.map((value, index) => ({
    name: value.value || '(leer)',
    value: value.count,
    key: 'value-' + index,
  }));
  const rest = profile.rows - column.missing - values.reduce((sum, v) => sum + v.value, 0);
  if (rest > 0) values.push({ name: 'Übrige Werte (zusammen)', value: rest, key: 'rest' });
  if (column.missing > 0)
    values.push({ name: 'Fehlende Werte (zusammen)', value: column.missing, key: 'missing' });
  return values;
}

export function numericPoints(sample: ChartSample | undefined, min: string, max: string) {
  const lower = min === '' ? null : numericValue(min);
  const upper = max === '' ? null : numericValue(max);
  const invalid =
    (min !== '' && lower === null) ||
    (max !== '' && upper === null) ||
    (lower !== null && upper !== null && lower > upper);
  const valid = (sample?.rows ?? []).flatMap((row) => {
    const x = numericValue(row.values[0]),
      y = numericValue(row.values[1]);
    return x === null ? [] : [{ row: row.row_number, x, y }];
  });
  const filtered = invalid
    ? []
    : valid.filter((p) => (lower === null || p.x >= lower) && (upper === null || p.x <= upper));
  return { points: filtered, excluded: (sample?.rows.length ?? 0) - valid.length, invalid };
}

export function histogram(values: number[], bins: number) {
  if (!values.length) return [];
  const low = Math.min(...values),
    high = Math.max(...values);
  if (low === high) return [{ name: numberLabel(low), value: values.length }];
  const width = (high - low) / bins;
  if (width === 0)
    return [{ name: numberLabel(low) + ' bis ' + numberLabel(high), value: values.length }];
  const counts = Array.from({ length: bins }, () => 0);
  values.forEach((v) => counts[Math.min(bins - 1, Math.floor((v - low) / width))]++);
  return counts.map((value, i) => ({
    name: numberLabel(low + i * width) + ' bis ' + numberLabel(low + (i + 1) * width),
    value,
  }));
}
