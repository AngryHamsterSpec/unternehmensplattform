import type { Group, Decimal, Role } from './types';
export const groups: Record<Group, string> = {
  cost: 'Kosten',
  performance: 'Leistung',
  resilience: 'Resilienz',
  operations: 'Betrieb',
  governance: 'Sicherheit & Steuerung',
};
export const groupKeys = Object.keys(groups) as Group[];
export const roles: Record<Role, string> = {
  ORG_ADMIN: 'Administration',
  ARCHITECTURE_ANALYST: 'Architekturanalyse',
  VIEWER: 'Lesen',
};
export const profiles = {
  ECONOMIC: 'Wirtschaftlichkeit',
  PERFORMANCE: 'Leistung',
  CUSTOM: 'Eigene Gewichte',
};
export function number(value: Decimal | number | undefined, digits = 2): string {
  if (value === null || value === undefined || value === '') return 'Unbekannt';
  const parsed = Number(value);
  return Number.isFinite(parsed)
    ? new Intl.NumberFormat('de-DE', { maximumFractionDigits: digits }).format(parsed)
    : 'Unbekannt';
}
export function money(value: Decimal | undefined): string {
  if (value === null || value === undefined || value === '') return 'Nicht berechenbar';
  // Format only. All financial arithmetic belongs to the server's Decimal engine.
  return new Intl.NumberFormat('de-DE', { style: 'currency', currency: 'EUR' }).format(
    Number(value),
  );
}
export function date(value: string) {
  return new Intl.DateTimeFormat('de-DE', { dateStyle: 'medium', timeStyle: 'short' }).format(
    new Date(value),
  );
}
export function decimal(value: string): Decimal {
  return value.trim() === '' ? null : value.replace(',', '.');
}
export function integer(value: string): number | null {
  return value === '' ? null : Number(value);
}
