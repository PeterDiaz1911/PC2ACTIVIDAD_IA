import { useState, type FormEvent } from 'react';
import { Activity, AlertCircle, CheckCircle2 } from 'lucide-react';
import type { FeatureSchema, Models, Prediction } from '../api';
import { api } from '../api';
import Panel from '../components/Panel';
import { StateMessage } from '../components/StateMessage';

export default function PredictionPage({ models }: { models: Models | null }) {
  const [values, setValues] = useState<Record<string, string>>({});
  const [result, setResult] = useState<Prediction | null>(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  if (!models || models.status === 'pending' || !models.model_available || !models.input_schema?.length) {
    return <StateMessage kind="pending">{models?.message ?? 'Predicción individual no disponible: no hay un pipeline entrenado. Ejecuta npm run analysis para generarlo; no se simulan predicciones.'}</StateMessage>;
  }
  const inputSchema = models.input_schema;

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError('');
    setResult(null);
    const features: Record<string, string | number | null> = {};
    for (const field of inputSchema) {
      const value = values[field.name]?.trim() ?? '';
      if (!value) {
        features[field.name] = null;
      } else if (field.kind === 'number') {
        const number = Number(value);
        if (!Number.isFinite(number)) {
          setError(`${field.name} debe ser un número finito.`);
          return;
        }
        features[field.name] = number;
      } else {
        features[field.name] = value;
      }
    }
    setBusy(true);
    try {
      setResult(await api.predict(features));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'No se pudo calcular la estimación.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="row g-3">
      <div className="col-12">
        <div className="notice notice--warning">Estimación del caso académico. Los campos vacíos se imputan dentro del pipeline. No se solicita la variable cancelo. La validez temporal depende de que las variables estuvieran disponibles antes de una cancelación; el dataset no demuestra esa secuencia.</div>
      </div>
      <div className="col-12 col-xl-8">
        <Panel title="Perfil de suscripción" description={`Formulario generado desde el pipeline ${models.model_version ?? ''}. Categorías nuevas son admitidas por el codificador.`}>
          <form onSubmit={submit} noValidate>
            <div className="row g-3">
              {inputSchema.map((field) => <div className="col-12 col-md-6" key={field.name}>
                <FeatureField field={field} value={values[field.name] ?? ''} onChange={(value) => setValues((current) => ({ ...current, [field.name]: value }))} />
              </div>)}
              <div className="col-12">
                <button className="btn btn-netflix" type="submit" disabled={busy}>
                  {busy ? <Activity size={17} className="spin" /> : null}
                  {busy ? 'Calculando…' : 'Estimar cancelación'}
                </button>
              </div>
            </div>
          </form>
          {error && <div className="notice notice--error mt-3" role="alert"><AlertCircle size={18} />{error}</div>}
        </Panel>
      </div>
      <div className="col-12 col-xl-4">
        <Panel title="Resultado de estimación">
          {!result ? <StateMessage kind="empty">Completa el perfil y solicita una estimación. El modelo no se entrena al abrir esta pantalla.</StateMessage> : (
            <div className="prediction-result" role="status">
              <CheckCircle2 size={22} className="text-netflix" />
              <span className="prediction-label">Clase estimada</span>
              <strong>{result.label}</strong>
              <span className="prediction-probability">{result.probability_estimate === null ? 'Puntuación no disponible' : `${(result.probability_estimate * 100).toFixed(1)}%`}<small> puntuación estimada para cancelo=1</small></span>
              <div className="probability-track" aria-label={result.probability_estimate === null ? 'Puntuación no disponible' : `Puntuación aproximada ${(result.probability_estimate * 100).toFixed(1)} por ciento`}>
                <span style={{ width: `${Math.max(0, Math.min(100, (result.probability_estimate ?? 0) * 100))}%` }} />
              </div>
              <p className="small text-secondary mb-0">Umbral utilizado: {result.threshold.toFixed(2)} · Modelo {result.model_version}</p>
              <p className="small text-secondary mt-2 mb-0">{result.calibration_note}</p>
            </div>
          )}
        </Panel>
      </div>
    </div>
  );
}

function FeatureField({ field, value, onChange }: { field: FeatureSchema; value: string; onChange: (value: string) => void }) {
  const id = `feature-${field.name}`;
  if (field.kind === 'category') {
    return (
      <div>
        <label className="form-label" htmlFor={id}>{field.name.replace(/_/g, ' ')}</label>
        <input
          id={id}
          className="form-control form-control-dark"
          type="text"
          list={`${id}-options`}
          value={value}
          onChange={(event) => onChange(event.target.value)}
          placeholder="Escribe una categoría o deja vacío"
          autoComplete="off"
        />
        <datalist id={`${id}-options`}>{field.options?.map((option) => <option value={option} key={option} />)}</datalist>
      </div>
    );
  }
  return (
    <div>
      <label className="form-label" htmlFor={id}>{field.name.replace(/_/g, ' ')}</label>
      <input
        id={id}
        className="form-control form-control-dark"
        type="number"
        step="any"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder="Número o vacío"
        inputMode="decimal"
      />
      <div className="form-text">Rango observado en entrenamiento: {field.minimum ?? '—'} a {field.maximum ?? '—'}. Es una referencia, no un límite obligatorio.</div>
    </div>
  );
}
