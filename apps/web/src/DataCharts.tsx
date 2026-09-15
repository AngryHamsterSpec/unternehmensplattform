import { useEffect, useMemo, useRef, useState } from 'react';
import * as echarts from 'echarts/core';
import { BarChart, PieChart, LineChart, ScatterChart } from 'echarts/charts';
import {
  AriaComponent,
  DataZoomComponent,
  GridComponent,
  LegendComponent,
  TitleComponent,
  TooltipComponent,
} from 'echarts/components';
import { CanvasRenderer, SVGRenderer } from 'echarts/renderers';
import type { EChartsCoreOption, EChartsType } from 'echarts/core';
import type { ChartSample, VersionView } from './generated/domain';
import { ErrorNotice, Field, Loading } from './components';
import { useLoad } from './useLoad';
import {
  chartNames,
  frequencies,
  histogram,
  numberLabel,
  numericPoints,
  shortLabel,
} from './chartModel';
import type { ChartKind } from './chartModel';
import './charts.css';
import { Icon } from './DesignSystem';
import { chartTheme } from './chartTheme';

echarts.use([
  BarChart,
  PieChart,
  LineChart,
  ScatterChart,
  AriaComponent,
  DataZoomComponent,
  GridComponent,
  LegendComponent,
  TitleComponent,
  TooltipComponent,
  CanvasRenderer,
  SVGRenderer,
]);

export default function DataCharts({ id, version }: { id: string; version: VersionView }) {
  const profile = version.profile;
  const numeric = profile.columns.flatMap((column, index) =>
    column.inferred_type === 'decimal' ? [index] : [],
  );
  const [kind, setKind] = useState<ChartKind>('bar');
  const [column, setColumn] = useState(
    Math.max(
      0,
      profile.columns.findIndex((c) => c.inferred_type === 'text'),
    ),
  );
  const [x, setX] = useState(numeric[0] ?? 0);
  const [y, setY] = useState(numeric[1] ?? numeric[0] ?? 0);
  const [interactive, setInteractive] = useState(true);
  const [expanded, setExpanded] = useState(false);
  const [minimum, setMinimum] = useState('');
  const [maximum, setMaximum] = useState('');
  const [bins, setBins] = useState(12);
  const [revision, setRevision] = useState(0);
  const [exportError, setExportError] = useState<unknown>();
  const chart = useRef<EChartsType | null>(null);
  const sampled = ['histogram', 'line', 'scatter'].includes(kind);
  const panel = useRef<HTMLElement>(null);
  return (
    <section
      className={'visual-workbench' + (expanded ? ' visual-expanded' : '')}
      ref={panel}
      aria-label="Visuelle Datenanalyse"
    >
      <header className="visual-heading">
        <div>
          <p className="eyebrow">DATEN EXPLORIEREN · VERSION {version.version_no}</p>
          <h2>Visuelle Analyse</h2>
          <p>Zusammenhänge entdecken. Zahlen nachvollziehen.</p>
        </div>
        <span className="visual-badge">
          ● {sampled ? 'Detailanalyse · bis 300 Zeilen' : 'Vollständiges Datenprofil'}
        </span>
      </header>
      <div className="visual-kpis">
        <div>
          <span>ZEILEN GESAMT</span>
          <strong>{profile.rows.toLocaleString('de-DE')}</strong>
        </div>
        <div>
          <span>SPALTEN</span>
          <strong>{profile.columns.length}</strong>
        </div>
        <div>
          <span>VOLLSTÄNDIG</span>
          <strong>
            {profile.completeness_percent.replace('.', ',')} <small>%</small>
          </strong>
        </div>
        <div>
          <span>NUMERISCHE SPALTEN</span>
          <strong>{numeric.length}</strong>
        </div>
      </div>
      <div className="visual-types" role="group" aria-label="Diagrammtyp">
        {(Object.keys(chartNames) as ChartKind[]).map((value) => (
          <button
            key={value}
            type="button"
            aria-pressed={kind === value}
            disabled={['histogram', 'line', 'scatter'].includes(value) && !numeric.length}
            onClick={() => {
              setKind(value);
              setExportError(undefined);
            }}
          >
            <Icon name={value === 'quality' ? 'data' : value === 'histogram' ? 'bar' : value} />
            {chartNames[value]}
          </button>
        ))}
      </div>
      <div className="visual-controls">
        {!sampled && kind !== 'quality' && (
          <Field label="Diagrammspalte">
            <select value={column} onChange={(e) => setColumn(Number(e.target.value))}>
              {profile.columns.map((c, i) => (
                <option key={i} value={i}>
                  {c.name}
                </option>
              ))}
            </select>
          </Field>
        )}
        {sampled && (
          <Field label={kind === 'scatter' ? 'X-Achse' : 'Messwert'}>
            <select
              value={x}
              onChange={(e) => {
                setX(Number(e.target.value));
                setMinimum('');
                setMaximum('');
              }}
            >
              {numeric.map((i) => (
                <option key={i} value={i}>
                  {profile.columns[i].name}
                </option>
              ))}
            </select>
          </Field>
        )}
        {kind === 'scatter' && (
          <Field label="Y-Achse">
            <select value={y} onChange={(e) => setY(Number(e.target.value))}>
              {numeric.map((i) => (
                <option key={i} value={i}>
                  {profile.columns[i].name}
                </option>
              ))}
            </select>
          </Field>
        )}
        <Field label="Darstellung">
          <select
            aria-label="Darstellung"
            value={interactive ? 'interactive' : 'static'}
            onChange={(e) => setInteractive(e.target.value === 'interactive')}
          >
            <option value="interactive">Interaktiv · Zoom & Details</option>
            <option value="static">Präsentation · statisch</option>
          </select>
        </Field>
        <button
          className="secondary"
          onClick={() => {
            setExpanded(!expanded);
          }}
        >
          {' '}
          {expanded ? 'Ansicht verkleinern' : 'Ansicht vergrößern'}
        </button>
      </div>
      {sampled && (
        <div className="visual-filters">
          <Field label="Messwert ab" hint="Dezimalpunkt">
            <input
              type="text"
              inputMode="decimal"
              value={minimum}
              onChange={(e) => setMinimum(e.target.value)}
              placeholder="Ohne Untergrenze"
            />
          </Field>
          <Field label="Messwert bis" hint="Dezimalpunkt">
            <input
              type="text"
              inputMode="decimal"
              value={maximum}
              onChange={(e) => setMaximum(e.target.value)}
              placeholder="Ohne Obergrenze"
            />
          </Field>
          {kind === 'histogram' && (
            <Field label="Klassen">
              <select value={bins} onChange={(e) => setBins(Number(e.target.value))}>
                {[6, 12, 20, 30].map((n) => (
                  <option key={n} value={n}>
                    {n} Klassen
                  </option>
                ))}
              </select>
            </Field>
          )}
          <button
            className="text-button"
            onClick={() => {
              setMinimum('');
              setMaximum('');
            }}
          >
            Filter zurücksetzen
          </button>
        </div>
      )}
      {sampled ? (
        <SamplePlot
          key={x + ':' + y}
          id={id}
          version={version}
          x={x}
          y={kind === 'scatter' ? y : x}
          kind={kind}
          interactive={interactive}
          minimum={minimum}
          maximum={maximum}
          bins={bins}
          chart={chart}
          revision={revision}
        />
      ) : (
        <Plot
          version={version}
          kind={kind}
          column={column}
          interactive={interactive}
          chart={chart}
          revision={revision}
        />
      )}
      <div className="visual-actions">
        {interactive && (
          <button className="secondary" onClick={() => setRevision((v) => v + 1)}>
            Zoom zurücksetzen
          </button>
        )}
        <button className="secondary" onClick={() => exportImage('svg')}>
          SVG exportieren
        </button>
        <button onClick={() => exportImage('png')}>PNG exportieren</button>
      </div>
      <ErrorNotice error={exportError} />
      <p className="form-hint visual-provenance">
        Quelle: gespeicherte Version {version.version_no} · SHA-256{' '}
        {version.content_hash.slice(0, 16)}… · Bildexport mit Datenbasis und aktiver Ansicht.
      </p>
    </section>
  );
  function exportImage(format: 'svg' | 'png') {
    setExportError(undefined);
    if (!chart.current || chart.current.isDisposed()) {
      setExportError(new Error('Das Diagramm ist noch nicht bereit.'));
      return;
    }
    let rendered: EChartsType | undefined;
    try {
      const element = document.createElement('div');
      rendered = echarts.init(element, undefined, {
        renderer: format === 'svg' ? 'svg' : 'canvas',
        width: Math.max(900, chart.current.getWidth()),
        height: 600,
        ssr: format === 'svg',
      });
      rendered.setOption({ ...chart.current.getOption(), animation: false });
      rendered.setOption({
        title: {
          textStyle: { width: Math.max(900, chart.current.getWidth()) - 36, overflow: 'break' },
          subtextStyle: { width: Math.max(900, chart.current.getWidth()) - 36, overflow: 'break' },
        },
      });
      const anchor = document.createElement('a');
      anchor.download = 'diagramm-v' + version.version_no + '-' + kind + '.' + format;
      anchor.href =
        format === 'svg'
          ? URL.createObjectURL(new Blob([rendered.renderToSVGString()], { type: 'image/svg+xml' }))
          : rendered.getDataURL({ type: 'png', pixelRatio: 2, backgroundColor: '#ffffff' });
      document.body.append(anchor);
      anchor.click();
      anchor.remove();
      if (format === 'svg') {
        const url = anchor.href;
        window.setTimeout(() => URL.revokeObjectURL(url), 1000);
      }
    } catch {
      setExportError(
        new Error('Das Diagramm konnte nicht exportiert werden. Bitte erneut versuchen.'),
      );
    } finally {
      rendered?.dispose();
    }
  }
}

type ChartRef = { current: EChartsType | null };
function SamplePlot(props: {
  id: string;
  version: VersionView;
  x: number;
  y: number;
  kind: ChartKind;
  interactive: boolean;
  minimum: string;
  maximum: string;
  bins: number;
  chart: ChartRef;
  revision: number;
}) {
  const [retry, setRetry] = useState(0);
  const { data, error } = useLoad<ChartSample>(
    '/datasets/' +
      props.id +
      '/versions/' +
      props.version.version_no +
      '/chart-sample?x=' +
      props.x +
      '&y=' +
      props.y,
    retry,
  );
  if (error) return <ErrorNotice error={error} retry={() => setRetry((v) => v + 1)} />;
  if (!data) return <Loading />;
  if (data.content_hash !== props.version.content_hash)
    return (
      <ErrorNotice
        error={
          new Error('Die Diagrammdaten gehören nicht zur ausgewählten Version. Bitte neu laden.')
        }
      />
    );
  return <Plot {...props} sample={data} column={props.x} />;
}

function Plot({
  version,
  kind,
  column,
  interactive,
  chart,
  revision,
  sample,
  minimum = '',
  maximum = '',
  bins = 12,
}: {
  version: VersionView;
  kind: ChartKind;
  column: number;
  interactive: boolean;
  chart: ChartRef;
  revision: number;
  sample?: ChartSample;
  minimum?: string;
  maximum?: string;
  bins?: number;
}) {
  const host = useRef<HTMLDivElement>(null);
  const model = useMemo(() => {
    const theme = chartTheme();
    const profile = version.profile;
    const numeric = numericPoints(sample, minimum, maximum);
    const points = kind === 'scatter' ? numeric.points.filter((p) => p.y !== null) : numeric.points;
    const exact = !sample || sample.method === 'complete';
    const basis = !sample
      ? 'Vollständiges Profil · ' + profile.rows.toLocaleString('de-DE') + ' Zeilen'
      : (exact ? 'Alle ' : 'Systematische Auswahl · ') +
        sample.rows.length.toLocaleString('de-DE') +
        ' von ' +
        profile.rows.toLocaleString('de-DE') +
        ' Zeilen · sichtbar: ' +
        points.length +
        ' · Filter: ' +
        (minimum || '−∞') +
        ' bis ' +
        (maximum || '+∞');
    const name =
      kind === 'quality'
        ? 'Vollständigkeit nach Spalte'
        : kind === 'line'
          ? profile.columns[column].name + ' nach Zeilenposition'
          : kind === 'scatter'
            ? sample?.columns.join(' × ')
            : profile.columns[column].name;
    const groups =
      kind === 'quality'
        ? profile.columns.map((c) => ({ name: c.name, value: profile.rows - c.missing }))
        : kind === 'histogram'
          ? histogram(
              points.map((p) => p.x),
              bins,
            )
          : frequencies(profile, column);
    const entries: (string | number)[][] =
      sample && kind !== 'histogram'
        ? points.map((p) => (kind === 'scatter' ? [p.row, p.x, p.y ?? ''] : [p.row, p.x]))
        : groups.map((v, i) =>
            kind === 'quality' ? [v.name, v.value, profile.columns[i].missing] : [v.name, v.value],
          );
    const headers =
      sample && kind !== 'histogram'
        ? [
            'Originalzeile',
            ...(kind === 'scatter' ? sample.columns : [profile.columns[column].name]),
          ]
        : kind === 'quality'
          ? ['Spalte', 'Belegt', 'Fehlend']
          : ['Wert / Klasse', 'Anzahl'];
    const horizontal = kind === 'bar' || kind === 'quality';
    const compactTitle = shortLabel(name ?? '', 65);
    const option: EChartsCoreOption = {
      color: theme.colors,
      backgroundColor: '#ffffff',
      animation: false,
      textStyle: { fontFamily: theme.font, color: theme.ink },
      title: {
        text: compactTitle,
        subtext:
          basis +
          '\nVersion ' +
          version.version_no +
          ' · SHA-256 ' +
          version.content_hash.slice(0, 12),
        left: 18,
        top: 15,
        textStyle: { fontSize: 17, fontWeight: 600 },
        subtextStyle: { fontSize: 11, lineHeight: 17, color: theme.muted },
      },
      aria: {
        enabled: true,
        label: {
          description:
            compactTitle + '. ' + basis + '. Werte stehen in der Tabelle unter dem Diagramm.',
        },
        decal: { show: kind === 'donut' },
      },
      tooltip: {
        show: interactive,
        trigger: kind === 'line' || kind === 'histogram' ? 'axis' : 'item',
        renderMode: 'richText',
        confine: true,
      },
      legend: {
        show: kind === 'donut' || kind === 'quality',
        bottom: 6,
        type: 'scroll',
        selectedMode: interactive,
        textStyle: { color: theme.muted },
      },
      grid: {
        left: horizontal ? 140 : 65,
        right: 38,
        top: 110,
        bottom: interactive ? 90 : 60,
        containLabel: false,
      },
    };
    if (kind === 'donut') {
      option.series = [
        {
          type: 'pie',
          radius: ['40%', '66%'],
          center: ['50%', '53%'],
          minAngle: 1,
          stillShowZeroSum: false,
          avoidLabelOverlap: true,
          silent: !interactive,
          label: { show: false },
          itemStyle: { borderColor: '#fff', borderWidth: 3, borderRadius: 2 },
          data: groups.map((g, i) => ({
            name: shortLabel(g.name, 45) + ' · ' + (i + 1),
            value: g.value,
          })),
          emphasis: {
            scale: interactive,
            label: { show: interactive, formatter: '{b}\n{d} %', fontSize: 13 },
          },
        },
      ];
    } else if (kind === 'scatter' || kind === 'line') {
      const scatter = kind === 'scatter';
      option.xAxis = {
        type: 'value',
        name: scatter ? shortLabel(sample?.columns[0] ?? '', 20) : 'Originalzeile',
        nameLocation: 'middle',
        nameGap: 32,
        scale: true,
        axisLabel: { formatter: numberLabel },
        splitLine: { lineStyle: { color: theme.grid } },
      };
      option.yAxis = {
        type: 'value',
        scale: true,
        name: shortLabel((scatter ? sample?.columns[1] : profile.columns[column].name) ?? '', 20),
        axisLabel: { formatter: numberLabel },
        splitLine: { lineStyle: { color: theme.grid } },
      };
      option.series = [
        {
          name: scatter ? 'Messwerte' : 'Wert',
          type: scatter ? 'scatter' : 'line',
          symbolSize: scatter ? 9 : 5,
          silent: !interactive,
          smooth: false,
          connectNulls: false,
          lineStyle: { width: 2 },
          areaStyle: scatter ? undefined : { opacity: 0.07 },
          data: scatter ? points.map((p) => [p.x, p.y]) : numeric.points.map((p) => [p.row, p.x]),
        },
      ];
    } else {
      const category = {
        type: 'category',
        data: groups.map((v) => shortLabel(v.name, horizontal ? 21 : 18)),
        axisLabel: { color: theme.muted, fontSize: 11, rotate: kind === 'histogram' ? 22 : 0 },
        axisLine: { show: false },
        axisTick: { show: false },
      };
      const value = {
        type: 'value',
        min: 0,
        axisLabel: { formatter: numberLabel },
        splitLine: { lineStyle: { color: theme.grid } },
        name: 'Zeilen',
      };
      option.xAxis = horizontal ? value : category;
      option.yAxis = horizontal ? { ...category, inverse: true } : value;
      option.series = [
        {
          name: kind === 'quality' ? 'Belegt' : 'Anzahl',
          type: 'bar',
          stack: 'quality',
          barMaxWidth: 26,
          silent: !interactive,
          itemStyle: { borderRadius: kind === 'quality' ? 0 : 2 },
          data: groups.map((g) => g.value),
        },
        ...(kind === 'quality'
          ? [
              {
                name: 'Fehlend',
                type: 'bar',
                stack: 'quality',
                barMaxWidth: 26,
                silent: !interactive,
                itemStyle: { color: theme.warning },
                data: profile.columns.map((c) => c.missing),
              },
            ]
          : []),
      ];
    }
    if (interactive && kind !== 'donut') {
      option.dataZoom = [
        {
          type: 'slider',
          ...(horizontal
            ? { yAxisIndex: 0, right: 5, top: 110, bottom: 80, width: 14 }
            : { xAxisIndex: 0, bottom: 22, height: 22 }),
          start: 0,
          end: kind === 'quality' && groups.length > 12 ? (12 / groups.length) * 100 : 100,
          borderColor: theme.border,
          fillerColor: 'rgba(18,108,104,0.12)',
          showDetail: false,
        },
        {
          type: 'inside',
          ...(horizontal ? { yAxisIndex: 0 } : { xAxisIndex: 0 }),
          zoomOnMouseWheel: 'ctrl',
          moveOnMouseWheel: false,
          moveOnMouseMove: true,
        },
      ];
    }
    return {
      option,
      basis,
      entries,
      headers,
      invalid: numeric.invalid,
      excluded: (sample?.rows.length ?? 0) - points.length,
    };
  }, [version, kind, column, interactive, sample, minimum, maximum, bins]);
  useEffect(() => {
    if (!host.current) return;
    const instance = echarts.init(host.current, undefined, { renderer: 'svg' });
    chart.current = instance;
    instance.setOption(model.option);
    const fit = () => {
      instance.resize();
      const width = Math.max(120, instance.getWidth() - 36);
      instance.setOption({
        title: {
          textStyle: { width, overflow: 'truncate' },
          subtextStyle: { width, overflow: 'break', fontSize: width < 430 ? 10 : 11 },
        },
        grid: {
          top: width < 430 ? 140 : 110,
          left: kind === 'bar' || kind === 'quality' ? Math.min(140, width * 0.35) : 60,
        },
      });
    };
    fit();
    const resize = new ResizeObserver(fit);
    resize.observe(host.current);
    return () => {
      resize.disconnect();
      instance.dispose();
      if (chart.current === instance) chart.current = null;
    };
  }, [model, chart, revision, kind]);
  return (
    <div className="visual-plot">
      {model.invalid && (
        <p className="notice error" role="alert">
          Bitte gültige Grenzen eingeben; die Untergrenze darf nicht über der Obergrenze liegen.
        </p>
      )}
      <div className="visual-canvas" ref={host} data-testid="data-chart" />
      <p className="visual-basis">{model.basis}</p>
      {sample && (
        <p className="form-hint">
          {sample.method === 'complete'
            ? 'Alle Zeilen dieser Datenversion sind in der Auswahl enthalten.'
            : 'Maximal 300 Zeilen aus bis zu zwölf über die Datei verteilten Abschnitten. Keine Zufallsstichprobe; Häufigkeiten und Trends können verzerrt sein.'}{' '}
          {model.excluded} Zeilen durch Filter oder fehlende/nicht darstellbare Messwerte
          ausgeschlossen.
          {sample.truncated_cells > 0 && ' Lange Textwerte sind auf 512 Zeichen gekürzt.'}{' '}
          Dezimalwerte werden nur für die Grafik angenähert. Die gespeicherten Originalwerte bleiben
          erhalten.
          {kind === 'line' &&
            ' Verbindungen folgen der Zeilenreihenfolge und überbrücken ausgelassene Zeilen; keine Zeitreihe.'}
        </p>
      )}
      {!sample && kind !== 'quality' && (
        <p className="form-hint">
          Die acht häufigsten belegten Originalwerte; übrige und fehlende Werte ergänzen die gesamte
          Zeilenzahl. Lange Beschriftungen sind gekürzt. Die Tabelle zeigt die Profilwerte.
        </p>
      )}
      {!model.entries.length && (
        <p className="notice info">
          Keine darstellbaren Werte für diese Auswahl. Bitte Spalten oder Filter ändern.
        </p>
      )}
      <details className="visual-table">
        <summary>Diagrammwerte als Tabelle</summary>
        <p className="form-hint">
          Alle Werte der aktuellen Filterauswahl; unabhängig vom sichtbaren Zoom.
        </p>
        <div className="table-scroll">
          <table>
            <caption>Werte der Visualisierung</caption>
            <thead>
              <tr>
                {model.headers.map((h, i) => (
                  <th key={i}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {model.entries.map((row, i) => (
                <tr key={i}>
                  {row.map((v, j) => (
                    <td key={j}>
                      {typeof v === 'number'
                        ? v.toLocaleString('de-DE', { maximumFractionDigits: 12 })
                        : v}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </div>
  );
}
