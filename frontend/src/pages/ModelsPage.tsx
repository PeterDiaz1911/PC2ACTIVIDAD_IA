import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import type { Models } from '../api';
import Panel from '../components/Panel';
import { StateMessage } from '../components/StateMessage';

const modelNames: Record<string, string> = {
  LogisticRegression: 'Regresión logística',
  RandomForestClassifier: 'Bosque aleatorio',
  DummyClassifier: 'Referencia simple',
};

export default function ModelsPage({ data }: { data: Models | null }) {
  if (!data || data.status === 'pending') return <StateMessage kind="pending">{data?.message ?? 'Evaluación pendiente. Ejecuta npm run analysis en la raíz.'}</StateMessage>;
  const chartRows = (data.metrics ?? []).map((item) => ({
    model: modelNames[item.modelo] ?? item.modelo,
    Exactitud: item.accuracy,
    Precisión: item.precision,
    Recall: item.recall,
    F1: item.f1,
  }));
  return (
    <div className="row g-3">
      <div className="col-12 col-xl-8">
        <Panel title="Comparación en conjunto de prueba" description="Métricas globales de la prueba reservada; no cambian con los filtros exploratorios.">
          <div className="model-chart">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartRows} margin={{ top: 14, right: 18, bottom: 4, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#29292f" vertical={false} />
                <XAxis dataKey="model" stroke="#a7a7ae" tick={{ fill: '#d0d0d5', fontSize: 12 }} />
                <YAxis domain={[0, 1]} tickFormatter={(value: number) => `${(value * 100).toFixed(0)}%`} stroke="#a7a7ae" tick={{ fill: '#a7a7ae', fontSize: 11 }} />
                <Tooltip contentStyle={{ background: '#1b1b20', border: '1px solid #34343c', borderRadius: 10, color: '#fff' }} formatter={(value: number) => [`${(value * 100).toFixed(1)}%`]} />
                <Legend />
                <Bar dataKey="Exactitud" fill="#777781" radius={[4, 4, 0, 0]} />
                <Bar dataKey="Precisión" fill="#b93740" radius={[4, 4, 0, 0]} />
                <Bar dataKey="Recall" fill="#e50914" radius={[4, 4, 0, 0]} />
                <Bar dataKey="F1" fill="#ee7278" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="table-responsive">
            <table className="table table-dark table-hover align-middle data-table mb-0">
              <thead><tr><th>Modelo</th><th className="text-end">Exactitud</th><th className="text-end">Precisión</th><th className="text-end">Recall</th><th className="text-end">F1</th></tr></thead>
              <tbody>{(data.metrics ?? []).filter((metric) => metric.modelo !== 'DummyClassifier').map((metric) => <tr key={metric.modelo}>
                <th scope="row">{modelNames[metric.modelo] ?? metric.modelo}</th><td className="text-end">{(metric.accuracy * 100).toFixed(2)}%</td><td className="text-end">{(metric.precision * 100).toFixed(2)}%</td><td className="text-end">{(metric.recall * 100).toFixed(2)}%</td><td className="text-end">{(metric.f1 * 100).toFixed(2)}%</td>
              </tr>)}</tbody>
            </table>
          </div>
        </Panel>
      </div>
      <div className="col-12 col-xl-4">
        <Panel title="Diseño de evaluación" description={`Versión de modelo ${data.model_version ?? '—'}`}>
          <dl className="evaluation-list">
            <div><dt>Entrenamiento</dt><dd>{((data.split?.train_fraction ?? 0) * 100).toFixed(0)}%</dd></div>
            <div><dt>Prueba reservada</dt><dd>{((data.split?.test_fraction ?? 0) * 100).toFixed(0)}% · {data.test_rows?.toLocaleString('es-PE') ?? '—'} usuarios</dd></div>
            <div><dt>Estratificación</dt><dd>{data.split?.stratified ? 'Sí, por cancelo' : 'No'}</dd></div>
            <div><dt>Semilla</dt><dd>{data.split?.random_state ?? '—'}</dd></div>
            <div><dt>Clase positiva</dt><dd>Canceló (1)</dd></div>
            <div><dt>Umbral</dt><dd>{data.threshold?.toFixed(2) ?? '—'}</dd></div>
          </dl>
          <p className="small text-secondary mb-0">La exactitud puede resultar engañosa si el modelo favorece la clase mayoritaria. La matriz de confusión muestra por separado las cancelaciones detectadas y omitidas.</p>
        </Panel>
      </div>
      {['LogisticRegression', 'RandomForestClassifier'].map((name) => <div className="col-12 col-xl-6" key={name}>
        <ConfusionMatrix name={name} data={data} />
      </div>)}
      <div className="col-12"><div className="notice notice--muted">{data.temporal_limitation}</div></div>
    </div>
  );
}

function ConfusionMatrix({ name, data }: { name: string; data: Models }) {
  const matrix = data.reports?.[name]?.confusion_matrix;
  if (!matrix || matrix.length !== 2) return <Panel title={modelNames[name]}><StateMessage kind="empty">Matriz de confusión no disponible.</StateMessage></Panel>;
  const [[tn, fp], [fn, tp]] = matrix;
  return (
    <Panel title={`Matriz de confusión · ${modelNames[name]}`} description="Filas: etiqueta real · columnas: predicción del modelo.">
      <div className="table-responsive">
        <table className="table table-dark table-bordered confusion-table text-center mb-0">
          <thead><tr><th scope="col">Real / Predicción</th><th scope="col">No cancela (0)</th><th scope="col">Sí cancela (1)</th></tr></thead>
          <tbody>
            <tr><th scope="row">No cancela (0)</th><td>{tn.toLocaleString('es-PE')}<small>Verdadero negativo</small></td><td>{fp.toLocaleString('es-PE')}<small>Falso positivo</small></td></tr>
            <tr><th scope="row">Sí cancela (1)</th><td>{fn.toLocaleString('es-PE')}<small>Falso negativo</small></td><td>{tp.toLocaleString('es-PE')}<small>Verdadero positivo</small></td></tr>
          </tbody>
        </table>
      </div>
      <p className="small text-secondary mt-3 mb-0">Un falso positivo implica contactar a alguien que no canceló; un falso negativo es una cancelación no identificada.</p>
    </Panel>
  );
}
