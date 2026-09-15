/** Diagramme und Bildexporte lesen dieselben semantischen Farbrollen wie die UI. */
export function chartTheme() {
  const style = getComputedStyle(document.documentElement);
  const token = (name: string) => style.getPropertyValue(name).trim();
  return {
    colors: Array.from({ length: 10 }, (_, i) => token('--chart-' + (i + 1))),
    font: token('--font-ui'),
    ink: token('--text-primary'),
    muted: token('--text-secondary'),
    grid: token('--chart-grid'),
    border: token('--border-subtle'),
    surface: token('--surface-panel'),
    warning: token('--chart-3'),
  };
}
