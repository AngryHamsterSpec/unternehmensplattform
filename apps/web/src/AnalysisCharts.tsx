import { useEffect, useRef, useState } from 'react';
import * as echarts from 'echarts/core';
import { BarChart, HeatmapChart, LineChart } from 'echarts/charts';
import {
  AriaComponent,
  DataZoomComponent,
  GridComponent,
  TooltipComponent,
  VisualMapComponent,
} from 'echarts/components';
import { SVGRenderer } from 'echarts/renderers';
import type { EChartsCoreOption, EChartsType } from 'echarts/core';
import type { AnalysisResult } from './generated/domain';
import { Field } from './components';
import { chartTheme } from './chartTheme';

echarts.use([
  BarChart,
  HeatmapChart,
  LineChart,
  AriaComponent,
  DataZoomComponent,
  GridComponent,
  TooltipComponent,
  VisualMapComponent,
  SVGRenderer,
]);
const short = (label: string) => (label.length > 20 ? label.slice(0, 19) + '…' : label);

export default function AnalysisCharts({ result }: { result: AnalysisResult }) {
  const [kind, setKind] = useState(result.numeric.length ? 'histogram' : 'time');
  const [column, setColumn] = useState(result.numeric[0]?.column ?? '');
  const [metric, setMetric] = useState('rows');
  const [interactive, setInteractive] = useState(true);
  const container = useRef<HTMLDivElement>(null);
  const chart = useRef<EChartsType | null>(null);
  const [themeVersion, setThemeVersion] = useState(0);
  useEffect(() => {
    const observer = new MutationObserver(() => setThemeVersion((v) => v + 1));
    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ['data-theme', 'class'],
    });
    return () => observer.disconnect();
  }, []);
  useEffect(() => {
    if (!container.current) return;
    const theme = chartTheme();
    const instance = echarts.init(container.current, undefined, { renderer: 'svg' });
    chart.current = instance;
    const option: EChartsCoreOption = {
      animation: false,
      color: theme.colors,
      backgroundColor: theme.surface,
      textStyle: { fontFamily: theme.font, color: theme.ink },
      aria: {
        enabled: true,
        label: {
          description:
            'Visualisierung der Vollanalyse. Sämtliche Werte stehen in den nachfolgenden barrierefreien Tabellen.',
        },
      },
      tooltip: {
        show: interactive,
        trigger: kind === 'correlation' ? 'item' : 'axis',
        renderMode: 'richText',
        confine: true,
      },
      grid: { left: 85, right: 35, top: 35, bottom: 85, containLabel: true },
    };
    const axis = {
      type: 'value',
      axisLabel: { color: theme.muted },
      splitLine: { lineStyle: { color: theme.grid } },
    };
    if (kind === 'correlation') {
      const names = result.numeric.map((n) => n.column);
      const data: number[][] = [];
      result.numeric.forEach((n, i) => {
        if (n.sample_stddev && Number(n.sample_stddev) > 0) data.push([i, i, 1]);
      });
      result.correlations.forEach((c) => {
        if (c.pearson !== null) {
          const x = names.indexOf(c.x);
          const y = names.indexOf(c.y);
          data.push([x, y, Number(c.pearson)], [y, x, Number(c.pearson)]);
        }
      });
      option.xAxis = {
        type: 'category',
        data: names,
        axisLabel: { formatter: short, rotate: 25, color: theme.muted },
        splitArea: { show: true },
      };
      option.yAxis = {
        type: 'category',
        data: names,
        axisLabel: { formatter: short, color: theme.muted },
      };
      option.visualMap = {
        min: -1,
        max: 1,
        dimension: 2,
        orient: 'horizontal',
        left: 'center',
        bottom: 0,
        calculable: interactive,
        inRange: { color: [theme.colors[2], theme.surface, theme.colors[0]] },
        textStyle: { color: theme.ink },
      };
      option.series = [
        {
          type: 'heatmap',
          data,
          silent: !interactive,
          label: {
            show: true,
            color: theme.ink,
            formatter: (p: { value: number[] }) => p.value[2].toFixed(2),
          },
          itemStyle: { borderColor: theme.border, borderWidth: 1 },
          emphasis: { itemStyle: { borderWidth: 2 } },
        },
      ];
    } else {
      let names: string[];
      let values: (number | null)[];
      if (kind === 'time') {
        names = result.time_series.periods.map((p) => p.period);
        values = result.time_series.periods.map((p) =>
          metric === 'rows'
            ? p.rows
            : p[metric === 'sum' ? 'sum' : 'mean'] === null
              ? null
              : Number(p[metric === 'sum' ? 'sum' : 'mean']),
        );
      } else {
        const n = result.numeric.find((v) => v.column === column) ?? result.numeric[0];
        names = Array.from({ length: 10 }, (_, i) =>
          n?.minimum === n?.maximum
            ? i === 0
              ? String(n?.minimum ?? '')
              : '—'
            : Number(
                Number(n?.minimum ?? 0) +
                  ((Number(n?.maximum ?? 0) - Number(n?.minimum ?? 0)) * i) / 10,
              ).toLocaleString('de-DE', { maximumSignificantDigits: 5 }) + ' …',
        );
        values = n?.histogram ?? [];
      }
      option.xAxis = {
        type: 'category',
        data: names,
        axisLabel: { color: theme.muted, rotate: 25 },
      };
      option.yAxis = {
        ...axis,
        min: kind === 'histogram' ? 0 : undefined,
        name:
          kind === 'histogram' || metric === 'rows'
            ? 'Zeilen'
            : metric === 'sum'
              ? 'Summe'
              : 'Mittelwert',
      };
      option.dataZoom = interactive
        ? [{ type: 'inside' }, { type: 'slider', bottom: 0, textStyle: { color: theme.muted } }]
        : [];
      option.series = [
        {
          type: kind === 'time' ? 'line' : 'bar',
          data: values,
          silent: !interactive,
          connectNulls: false,
          smooth: false,
          barMaxWidth: 42,
          symbolSize: 5,
        },
      ];
    }
    instance.setOption(option);
    const observer = new ResizeObserver(() => instance.resize());
    observer.observe(container.current);
    return () => {
      observer.disconnect();
      instance.dispose();
      chart.current = null;
    };
  }, [result, kind, column, metric, interactive, themeVersion]);
  if (!result.numeric.length && !result.time_series.periods.length) return null;
  function exportSvg() {
    if (!chart.current) return;
    const svg = chart.current.renderToSVGString();
    const url = URL.createObjectURL(new Blob([svg], { type: 'image/svg+xml' }));
    const link = document.createElement('a');
    link.href = url;
    link.download = 'vollanalyse-v' + result.version_no + '.svg';
    document.body.append(link);
    link.click();
    link.remove();
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  return (
    <div className="analysis-visual">
      <div className="data-fields">
        <Field label="Analysevisualisierung">
          <select value={kind} onChange={(e) => setKind(e.target.value)}>
            <option value="histogram">Histogramm · alle gültigen Werte</option>
            <option value="correlation">Korrelationsmatrix</option>
            <option value="time" disabled={!result.time_series.column}>
              Zeitverlauf
            </option>
          </select>
        </Field>
        {kind === 'histogram' && (
          <Field label="Histogrammspalte">
            <select value={column} onChange={(e) => setColumn(e.target.value)}>
              {result.numeric.map((n) => (
                <option key={n.column}>{n.column}</option>
              ))}
            </select>
          </Field>
        )}
        {kind === 'time' && (
          <Field label="Zeitverlaufswert">
            <select value={metric} onChange={(e) => setMetric(e.target.value)}>
              <option value="rows">Zeilen</option>
              <option value="sum" disabled={!result.time_series.metric}>
                Summe
              </option>
              <option value="mean" disabled={!result.time_series.metric}>
                Mittelwert
              </option>
            </select>
          </Field>
        )}
        <Field label="Diagramm-Modus">
          <select
            value={interactive ? 'interactive' : 'static'}
            onChange={(e) => setInteractive(e.target.value === 'interactive')}
          >
            <option value="interactive">Interaktiv</option>
            <option value="static">Statisch</option>
          </select>
        </Field>
      </div>
      <div
        ref={container}
        style={{ height: 390, width: '100%' }}
        aria-label="Diagramm der vollständigen Analyse"
      />
      <p className="form-hint">
        {kind === 'correlation'
          ? 'Pearson r von −1 bis +1; leere Felder sind nicht berechenbar. Farben und Zahlen gemeinsam lesen; keine Kausalitätsaussage.'
          : kind === 'time'
            ? 'UTC-Perioden; maximal erste 1.000 Perioden. Fehlende Perioden werden nicht ergänzt.'
            : 'Zehn gleich breite Klassen über sämtliche gültigen Werte. Achsengrenzen für die Ansicht gerundet.'}
      </p>
      <button className="secondary" onClick={exportSvg}>
        Analysediagramm als SVG
      </button>
    </div>
  );
}
