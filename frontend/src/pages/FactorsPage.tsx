import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import type { Factors } from '../api';
import Panel from '../components/Panel';
import { StateMessage } from '../components/StateMessage';

export default function FactorsPage({ data }: { data: Factors | null }) {
  if (!data || data.status === 'pending') return <StateMessage kind="pending">{data?.message ?? 'Importancia pendiente. Ejecuta npm run analysis en la raíz.'}</StateMessage>;
  const items = [...(data.items ?? [])].sort((a, b) => a.importancia_media - b.importancia_media);
  return (
    <div className="row g-3">
      <div className="col-12">
        <Panel title="Factores asociados a las predicciones" description={`Importancia por permutación de ${data.selected_model ?? 'modelo'} · métrica ${data.method?.scoring ?? '—'} · conjunto ${data.method?.dataset ?? '—'}.`}>
          {!items.length ? <StateMessage kind="empty">Importancia no disponible.</StateMessage> : (
            <div className="factor-chart">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={items} layout="vertical" margin={{ top: 12, right: 24, left: 90, bottom: 12 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#29292f" horizontal={false} />
                  <XAxis type="number" stroke="#a7a7ae" tick={{ fill: '#a7a7ae', fontSize: 11 }} />
                  <YAxis type="category" dataKey="variable" width={160} stroke="#a7a7ae" tick={{ fill: '#d0d0d5', fontSize: 12 }} />
                  <Tooltip contentStyle={{ background: '#1b1b20', border: '1px solid #34343c', borderRadius: 10, color: '#fff' }} formatter={(value: number) => [value.toFixed(4), 'Cambio medio en F1']} />
                  <Bar dataKey="importancia_media" name="Cambio medio en F1" fill="#e50914" radius={[0, 5, 5, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
          <div className="notice notice--muted mt-3">{data.causality_note}</div>
        </Panel>
      </div>
    </div>
  );
}
