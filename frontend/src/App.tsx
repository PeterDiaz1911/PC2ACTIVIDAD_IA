import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Activity, AlertTriangle, ArrowRight, BarChart3, ChevronDown, CircleHelp, Database, Download,
  Gauge, Layers3, Menu, MonitorDot, RotateCw, ShieldCheck, Target, Users, X,
} from 'lucide-react';
import { api, type DownloadItem, type Factors, type Health, type Models, type Quality, type SegmentResult, type Summary } from './api';
import MetricCard from './components/MetricCard';
import Panel from './components/Panel';
import { StateMessage } from './components/StateMessage';
import DownloadsPage from './pages/DownloadsPage';
import ExplorationPage from './pages/ExplorationPage';
import FactorsPage from './pages/FactorsPage';
import ModelsPage from './pages/ModelsPage';
import PredictionPage from './pages/PredictionPage';
import QualityPage from './pages/QualityPage';

type Section = 'overview' | 'quality' | 'exploration' | 'models' | 'factors' | 'prediction' | 'downloads';
const navigation: Array<{ id: Section; label: string; icon: typeof Gauge }> = [
  { id: 'overview', label: 'Resumen', icon: Gauge },
  { id: 'quality', label: 'Calidad de datos', icon: ShieldCheck },
  { id: 'exploration', label: 'Análisis exploratorio', icon: BarChart3 },
  { id: 'models', label: 'Modelos', icon: Layers3 },
  { id: 'factors', label: 'Factores asociados', icon: Target },
  { id: 'prediction', label: 'Predicción individual', icon: Activity },
  { id: 'downloads', label: 'Resultados y descargas', icon: Download },
];
const pageTitles: Record<Section, string> = {
  overview: 'Resumen',
  quality: 'Calidad de datos',
  exploration: 'Análisis exploratorio',
  models: 'Evaluación de modelos',
  factors: 'Factores asociados',
  prediction: 'Predicción individual',
  downloads: 'Resultados y descargas',
};

export default function App() {
  const [active, setActive] = useState<Section>('overview');
  const [mobileOpen, setMobileOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [fatalError, setFatalError] = useState('');
  const [refreshToken, setRefreshToken] = useState(0);
  const [health, setHealth] = useState<Health | null>(null);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [quality, setQuality] = useState<Quality | null>(null);
  const [models, setModels] = useState<Models | null>(null);
  const [factors, setFactors] = useState<Factors | null>(null);
  const [downloads, setDownloads] = useState<DownloadItem[]>([]);
  const [downloadError, setDownloadError] = useState('');
  const [filterOptions, setFilterOptions] = useState<{ countries: string[]; plans: string[]; devices: string[] }>({ countries: [], plans: [], devices: [] });
  const [filters, setFilters] = useState({ country: '', plan: '', device: '' });
  const [segments, setSegments] = useState<SegmentResult | null>(null);
  const [segmentError, setSegmentError] = useState('');
  const [segmentLoading, setSegmentLoading] = useState(false);

  const reload = useCallback(() => setRefreshToken((value) => value + 1), []);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setFatalError('');
    Promise.all([
      api.health(),
      api.summary(),
      api.quality(),
      api.filters(),
      api.models(),
      api.factors(),
      api.downloads(),
    ]).then(([healthData, summaryData, qualityData, filterData, modelData, factorsData, downloadData]) => {
      if (cancelled) return;
      setHealth(healthData);
      setSummary(summaryData);
      setQuality(qualityData);
      setModels(modelData);
      setFactors(factorsData);
      setDownloads(downloadData.items.filter((item) => item.available));
      setDownloadError('');
      if (filterData.status === 'ready') {
        setFilterOptions({ countries: filterData.countries, plans: filterData.plans, devices: filterData.devices });
      }
    }).catch((caught: unknown) => {
      if (cancelled) return;
      setFatalError(caught instanceof Error ? caught.message : 'No se pudo conectar con la API local.');
      setDownloadError(caught instanceof Error ? caught.message : 'No se pudo consultar la API local.');
    }).finally(() => {
      if (!cancelled) setLoading(false);
    });
    return () => { cancelled = true; };
  }, [refreshToken]);

  useEffect(() => {
    let cancelled = false;
    setSegmentLoading(true);
    setSegmentError('');
    api.segments(filters).then((result) => {
      if (!cancelled) setSegments(result);
    }).catch((caught: unknown) => {
      if (!cancelled) setSegmentError(caught instanceof Error ? caught.message : 'No se pudieron cargar los segmentos.');
    }).finally(() => {
      if (!cancelled) setSegmentLoading(false);
    });
    return () => { cancelled = true; };
  }, [filters, refreshToken]);

  const analysisReady = health?.analysis_status === 'ready' && summary?.status === 'ready';
  const updatedLabel = useMemo(() => formatDate(summary?.updated_at ?? health?.generated_at_utc ?? null), [summary?.updated_at, health?.generated_at_utc]);

  function chooseSection(section: Section) {
    setActive(section);
    setMobileOpen(false);
  }

  const page = (() => {
    if (active === 'overview') return <OverviewPage summary={summary} segments={segments} segmentLoading={segmentLoading} segmentError={segmentError} onNavigate={chooseSection} />;
    if (active === 'quality') return <QualityPage data={quality} />;
    if (active === 'exploration') return (
      <>
        <ExplorationFilters options={filterOptions} value={filters} onChange={setFilters} />
        {segmentLoading ? <StateMessage kind="loading">Actualizando métricas y gráficos para los filtros…</StateMessage> : segmentError ? <StateMessage kind="error">{segmentError}</StateMessage> : <ExplorationPage data={segments} />}
      </>
    );
    if (active === 'models') return <ModelsPage data={models} />;
    if (active === 'factors') return <FactorsPage data={factors} />;
    if (active === 'prediction') return <PredictionPage models={models} />;
    return <DownloadsPage items={downloads} error={downloadError} />;
  })();

  return (
    <div className="app-shell">
      {mobileOpen && <button className="offcanvas-backdrop fade show sidebar-scrim" type="button" aria-label="Cerrar menú" onClick={() => setMobileOpen(false)} />}
      <aside className={`sidebar offcanvas offcanvas-start ${mobileOpen ? 'show' : ''}`} role={mobileOpen ? 'dialog' : undefined} aria-modal={mobileOpen || undefined} aria-label="Navegación principal">
        <div className="brand">
          <img className="brand-logo" src="/assets/netflix-wordmark.png" alt="Netflix" />
          <strong className="brand-name">Churn Analytics</strong>
          <button className="mobile-close icon-button" aria-label="Cerrar menú" onClick={() => setMobileOpen(false)}><X size={19} /></button>
        </div>
        <div className="sidebar-caption">ANÁLISIS</div>
        <nav id="primary-navigation" className="nav flex-column app-nav">
          {navigation.map(({ id, label, icon: Icon }) => (
            <button key={id} className={`nav-link app-nav-link ${active === id ? 'active' : ''}`} aria-current={active === id ? 'page' : undefined} onClick={() => chooseSection(id)}>
              <Icon size={18} strokeWidth={1.8} aria-hidden="true" /><span>{label}</span>
              {id === 'overview' && <span className="nav-indicator" />}
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="source-chip"><Database size={15} /><span>Fuente local</span></div>
          <p>Proyecto académico no oficial.<br />No afiliado con Netflix.</p>
        </div>
      </aside>

      <main className="main-area">
        <header className="topbar">
          <button className="icon-button mobile-menu" aria-label="Abrir menú" aria-controls="primary-navigation" aria-expanded={mobileOpen} onClick={() => setMobileOpen(true)}><Menu size={21} /></button>
          <div className="topbar-title">
            <span className="eyebrow">ANÁLISIS DE CANCELACIONES <span className="eyebrow-divider">/</span> CASO ACADÉMICO</span>
            <h1>{pageTitles[active]}</h1>
          </div>
          <div className="topbar-status">
            <span className={`status-dot ${analysisReady ? 'status-dot--ready' : 'status-dot--pending'}`} />
            <span>{analysisReady ? `Datos actualizados ${updatedLabel}` : 'Análisis pendiente'}</span>
            <button className="icon-button refresh-button" aria-label="Actualizar resultados" title="Actualizar" onClick={reload}><RotateCw size={17} /></button>
          </div>
        </header>
        {fatalError && <div className="main-alert" role="alert"><AlertTriangle size={18} /><div><strong>API local no disponible.</strong> {fatalError}<span> Inicia ambos servicios con <code>npm run dev</code> desde la raíz del proyecto.</span></div><button className="icon-button" aria-label="Reintentar conexión" onClick={reload}><RotateCw size={16} /></button></div>}
        {loading ? <div className="page-content"><StateMessage kind="loading">Conectando con resultados locales…</StateMessage></div> : (
          <div className="page-content">
            {active !== 'overview' && <div className="section-heading">
              <div>
                <div className="section-kicker">{sectionCaption(active)}</div>
                <p>{sectionDescription(active)}</p>
              </div>
              {active !== 'exploration' && <div className="version-tag"><MonitorDot size={14} />{models?.model_version ? `Modelo ${models.model_version}` : 'Solo resultados locales'}</div>}
            </div>}
            {page}
            <footer className="page-footer">
              <span><CircleHelp size={14} /> Resultados del dataset académico proporcionado. No son métricas operativas de Netflix.</span>
              <span>Fuente: <code>neflix.csv</code></span>
            </footer>
          </div>
        )}
      </main>
    </div>
  );
}

function OverviewPage({ summary, segments, segmentLoading, segmentError, onNavigate }: {
  summary: Summary | null;
  segments: SegmentResult | null;
  segmentLoading: boolean;
  segmentError: string;
  onNavigate: (section: Section) => void;
}) {
  if (summary?.status === 'pending') return <StateMessage kind="pending">{summary.message ?? 'Análisis pendiente. Ejecuta npm run analysis desde la raíz del proyecto.'}</StateMessage>;
  const loading = segmentLoading || !segments;
  const data = segments?.status === 'ready' ? segments : null;
  return (
    <div className="row g-3">
      <div className="col-12">
        <section className="overview-hero" aria-labelledby="overview-title">
          <div className="overview-hero-copy">
            <span className="hero-kicker">NETFLIX CHURN ANALYTICS</span>
            <h2 id="overview-title">Comprende por qué cancelan tus usuarios</h2>
            <p>Explora los patrones de cancelación, compara segmentos y evalúa modelos con los resultados reales del dataset académico.</p>
            <div className="hero-actions">
              <button className="btn btn-netflix" onClick={() => onNavigate('exploration')}>Explorar análisis <ArrowRight size={16} /></button>
              <button className="btn btn-subtle" onClick={() => onNavigate('prediction')}>Evaluar un usuario <ArrowRight size={16} /></button>
            </div>
          </div>
          <div className="hero-context">Proyecto académico no oficial <span>·</span> Análisis descriptivo y predictivo</div>
        </section>
      </div>
      <div className="col-12 col-sm-6 col-xl-3">
        <MetricCard label="Usuarios analizados" value={loading ? '—' : data?.users.toLocaleString('es-PE') ?? '0'} note="Con etiqueta válida · filtros actuales" icon={Users} />
      </div>
      <div className="col-12 col-sm-6 col-xl-3">
        <MetricCard label="Cancelaciones observadas" value={loading ? '—' : data?.cancellations.toLocaleString('es-PE') ?? '0'} note="Usuarios con cancelo = 1" icon={Activity} tone="red" />
      </div>
      <div className="col-12 col-sm-6 col-xl-3">
        <MetricCard label="Tasa de cancelación" value={loading ? '—' : formatPercent(data?.cancellation_rate ?? null)} note="Proporción en la población filtrada" icon={BarChart3} tone="red" />
      </div>
      <div className="col-12 col-sm-6 col-xl-3">
        <MetricCard label="No cancelaron" value={loading ? '—' : data?.not_cancelled.toLocaleString('es-PE') ?? '0'} note="Usuarios con cancelo = 0" icon={ShieldCheck} tone="green" />
      </div>
      {segmentError && <div className="col-12"><StateMessage kind="error">{segmentError}</StateMessage></div>}
      {segments?.status === 'empty' && <div className="col-12"><StateMessage kind="empty">{segments.message ?? 'No hay usuarios para los filtros actuales.'}</StateMessage></div>}
      <div className="col-12 col-xl-7">
        <Panel title="Hallazgos principales" description="Mayor tasa descriptiva observada por grupo; no implica causalidad." actions={<button className="text-action" onClick={() => onNavigate('exploration')}>Ver segmentos <ChevronDown size={14} /></button>}>
          {summary?.findings?.length ? <div className="finding-list">{summary.findings.map((item) => <div className="finding-row" key={item.label}>
            <span className="finding-marker" /><div className="finding-copy"><span>{item.label}</span><strong>{item.group}</strong><small>{item.cancellations.toLocaleString('es-PE')} cancelaciones / {item.users.toLocaleString('es-PE')} usuarios</small></div><strong className="finding-rate">{formatPercent(item.rate)}</strong>
          </div>)}</div> : <StateMessage kind="pending">Hallazgos disponibles después de ejecutar el análisis.</StateMessage>}
        </Panel>
      </div>
      <div className="col-12 col-xl-5">
        <Panel title="Estado del conjunto" description="Los resultados provienen de una ejecución independiente del análisis.">
          <dl className="data-provenance">
            <div><dt>Origen</dt><dd>{summary?.source ?? 'data/raw/neflix.csv'}</dd></div>
            <div><dt>Última ejecución</dt><dd>{formatDate(summary?.updated_at ?? null)}</dd></div>
            <div><dt>Versión del modelo</dt><dd>{summary?.model_version ?? 'Pendiente'}</dd></div>
            <div><dt>Alcance</dt><dd>Dataset académico; no operativo</dd></div>
          </dl>
          <div className="notice notice--muted mt-3">Los indicadores de esta vista responden a filtros aplicados. Las métricas de modelo permanecen fijas sobre la partición de prueba.</div>
        </Panel>
      </div>
      <div className="col-12"><Panel title="Distribución de cancelación" description="Personas, no porcentaje."><CancellationBars segments={segments} /></Panel></div>
    </div>
  );
}

function CancellationBars({ segments }: { segments: SegmentResult | null }) {
  if (!segments || segments.status === 'pending') return <StateMessage kind="pending">{segments?.message ?? 'Análisis pendiente.'}</StateMessage>;
  if (segments.status === 'empty') return <StateMessage kind="empty">{segments.message ?? 'No hay usuarios para esta selección.'}</StateMessage>;
  const total = segments.users || 1;
  return <div className="distribution-bars">
    <div><span>No cancelaron</span><div className="distribution-track"><i className="distribution-fill distribution-fill--neutral" style={{ width: `${(segments.not_cancelled / total) * 100}%` }} /></div><strong>{segments.not_cancelled.toLocaleString('es-PE')}</strong></div>
    <div><span>Sí cancelaron</span><div className="distribution-track"><i className="distribution-fill distribution-fill--red" style={{ width: `${(segments.cancellations / total) * 100}%` }} /></div><strong>{segments.cancellations.toLocaleString('es-PE')}</strong></div>
  </div>;
}

function ExplorationFilters({ options, value, onChange }: {
  options: { countries: string[]; plans: string[]; devices: string[] };
  value: { country: string; plan: string; device: string };
  onChange: (value: { country: string; plan: string; device: string }) => void;
}) {
  const fields: Array<{ key: keyof typeof value; label: string; options: string[] }> = [
    { key: 'country', label: 'País', options: options.countries },
    { key: 'plan', label: 'Plan', options: options.plans },
    { key: 'device', label: 'Dispositivo', options: options.devices },
  ];
  return <div className="filter-bar mb-3">
    <div className="filter-heading"><span>Filtros de exploración</span><small>Se actualizan tarjetas, tasas, tablas y comparaciones.</small></div>
    <div className="filter-controls">{fields.map((field) => <div className="filter-control" key={field.key}>
      <label className="form-label" htmlFor={`filter-${field.key}`}>{field.label}</label>
      <select id={`filter-${field.key}`} className="form-select form-select-sm form-control-dark" value={value[field.key]} onChange={(event) => onChange({ ...value, [field.key]: event.target.value })}>
        <option value="">Todos</option>{field.options.map((option) => <option value={option} key={option}>{option}</option>)}
      </select>
    </div>)}
    <button className="btn btn-outline-light btn-sm clear-filters" onClick={() => onChange({ country: '', plan: '', device: '' })}>Limpiar filtros</button></div>
  </div>;
}

function sectionCaption(section: Section) {
  return section === 'overview' ? 'SALUD DE SUSCRIPCIONES' : section === 'exploration' ? 'PERFILES Y COMPORTAMIENTO' : 'RESULTADOS DEL CASO';
}

function sectionDescription(section: Section) {
  const values: Record<Section, string> = {
    overview: 'Resumen de los usuarios y las señales de cancelación observadas.',
    quality: 'Revisión de registros, valores ausentes y decisiones deterministas de limpieza.',
    exploration: 'Explora tasas de cancelación y compara comportamiento por segmento.',
    models: 'Evaluación sobre prueba reservada; la clase positiva es cancelo = 1.',
    factors: 'Variables asociadas a las predicciones del pipeline seleccionado.',
    prediction: 'Estimación de clase con el pipeline entrenado y persistido.',
    downloads: 'Descarga análisis, métricas y documentos generados por el pipeline local.',
  };
  return values[section];
}

function formatDate(value: string | null): string {
  if (!value) return 'Sin ejecución registrada';
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleString('es-PE', { dateStyle: 'medium', timeStyle: 'short' });
}

function formatPercent(value: number | null): string {
  return value === null || !Number.isFinite(value) ? '—' : `${(value * 100).toFixed(1)}%`;
}
