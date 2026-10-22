import { Bar, BarChart, CartesianGrid, Cell, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import type { SegmentResult } from '../api';
import Panel from '../components/Panel';
import { StateMessage } from '../components/StateMessage';

const GROUP_CHARTS = [
  { key: 'plan', title: 'Cancelación por plan', description: 'Porcentaje de usuarios de cada plan que canceló.' },
  { key: 'country', title: 'Cancelación por país', description: 'Tasa descriptiva y volumen de usuarios del grupo.' },
  { key: 'payment_method', title: 'Cancelación por método de pago', description: 'Tasa de cancelación según el medio de pago.' },
  { key: 'device', title: 'Cancelación por dispositivo', description: 'Tasa de cancelación por dispositivo principal.' },
] as const;

function RateChart({ title, description, data }: { title: string; description: string; data?: Array<{ group: string; users: number; cancellations: number; rate: number }> }) {
  return (
    <Panel title={title} description={description} className="chart-panel">
      {!data?.length ? <StateMessage kind="empty">No hay grupos con datos para los filtros seleccionados.</StateMessage> : (
        <>
          <div className="chart-legend-note"><span className="legend-dot legend-dot--red" /> Tasa de cancelación <span className="chart-units">%</span></div>
          <div className="chart-area">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data} margin={{ top: 12, right: 12, left: 0, bottom: 8 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#29292f" vertical={false} />
                <XAxis dataKey="group" stroke="#a7a7ae" tick={{ fill: '#b9b9c0', fontSize: 11 }} interval={0} angle={data.length > 4 ? -18 : 0} textAnchor={data.length > 4 ? 'end' : 'middle'} height={data.length > 4 ? 58 : 34} />
                <YAxis stroke="#a7a7ae" tick={{ fill: '#a7a7ae', fontSize: 11 }} tickFormatter={(value: number) => `${(value * 100).toFixed(0)}%`} domain={[0, 'auto']} />
                <Tooltip
                  cursor={{ fill: '#ffffff08' }}
                  contentStyle={{ background: '#1b1b20', border: '1px solid #34343c', borderRadius: 10, color: '#fff' }}
                  formatter={(value: number, _name: string, item) => [`${(value * 100).toFixed(1)}% · ${item.payload.cancellations}/${item.payload.users} usuarios`, 'Tasa']}
                />
                <Bar dataKey="rate" name="Tasa" radius={[5, 5, 0, 0]} maxBarSize={50}>
                  {data.map((item, index) => <Cell key={`${item.group}-${index}`} fill={index === 0 ? '#e50914' : '#a82c34'} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="table-responsive compact-table-wrap">
            <table className="table table-dark table-borderless table-sm align-middle compact-table mb-0">
              <thead><tr><th scope="col">Grupo</th><th className="text-end" scope="col">Usuarios</th><th className="text-end" scope="col">Canceló</th><th className="text-end" scope="col">Tasa</th></tr></thead>
              <tbody>{data.map((row) => <tr key={row.group}><th scope="row">{row.group}</th><td className="text-end">{row.users.toLocaleString('es-PE')}</td><td className="text-end">{row.cancellations.toLocaleString('es-PE')}</td><td className="text-end">{(row.rate * 100).toFixed(1)}%</td></tr>)}</tbody>
            </table>
          </div>
        </>
      )}
    </Panel>
  );
}

export function CancellationDistribution({ data }: { data: SegmentResult }) {
  const chartData = [
    { state: 'No cancela', users: data.not_cancelled },
    { state: 'Sí cancela', users: data.cancellations },
  ];
  return (
    <Panel title="Distribución de cancelación" description="Usuarios con etiqueta válida en la población filtrada." className="chart-panel">
      <div className="chart-legend-note"><span className="legend-dot legend-dot--muted" /> Usuarios <span className="chart-units">personas</span></div>
      <div className="chart-area">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} margin={{ top: 12, right: 12, left: 0, bottom: 8 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#29292f" vertical={false} />
            <XAxis dataKey="state" stroke="#a7a7ae" tick={{ fill: '#b9b9c0', fontSize: 12 }} />
            <YAxis stroke="#a7a7ae" tick={{ fill: '#a7a7ae', fontSize: 11 }} />
            <Tooltip contentStyle={{ background: '#1b1b20', border: '1px solid #34343c', borderRadius: 10, color: '#fff' }} formatter={(value: number) => [value.toLocaleString('es-PE'), 'Usuarios']} />
            <Bar dataKey="users" name="Usuarios" radius={[5, 5, 0, 0]} maxBarSize={78}>
              <Cell fill="#72727c" /><Cell fill="#e50914" />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </Panel>
  );
}

export default function ExplorationPage({ data }: { data: SegmentResult | null }) {
  if (!data || data.status === 'pending') return <StateMessage kind="pending">{data?.message ?? 'Análisis pendiente. Ejecuta npm run analysis en la raíz del proyecto.'}</StateMessage>;
  if (data.status === 'empty') return <StateMessage kind="empty">{data.message ?? 'No hay registros con estos filtros.'}</StateMessage>;
  return (
    <div className="row g-3">
      <div className="col-12"><CancellationDistribution data={data} /></div>
      {GROUP_CHARTS.map(({ key, title, description }) => (
        <div className="col-12 col-xl-6" key={key}>
          <RateChart title={title} description={description} data={data.groups[key]} />
        </div>
      ))}
      {data.behavior?.map((item) => (
        <div className="col-12 col-xl-6" key={item.variable}>
          <BehaviorChart item={item} />
        </div>
      ))}
    </div>
  );
}

function BehaviorChart({ item }: { item: NonNullable<SegmentResult['behavior']>[number] }) {
  return (
    <Panel title={item.label} description={`Mediana por estado · ${item.unit}; se excluyen nulos solo en esta comparación.`} className="chart-panel">
      <div className="chart-legend-note"><span className="legend-dot legend-dot--red" /> Sí cancela <span className="legend-dot legend-dot--muted ms-3" /> No cancela</div>
      <div className="chart-area chart-area--small">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={item.groups.map((group) => ({ ...group, group: group.state }))} margin={{ top: 12, right: 16, left: 0, bottom: 8 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#29292f" vertical={false} />
            <XAxis dataKey="group" stroke="#a7a7ae" tick={{ fill: '#b9b9c0', fontSize: 12 }} />
            <YAxis stroke="#a7a7ae" tick={{ fill: '#a7a7ae', fontSize: 11 }} />
            <Tooltip
              contentStyle={{ background: '#1b1b20', border: '1px solid #34343c', borderRadius: 10, color: '#fff' }}
              formatter={(value: number, _name: string, entry) => [`${value.toFixed(2)} ${item.unit} · n=${entry.payload.users}`, 'Mediana']}
            />
            <Legend />
            <Bar dataKey="median" name="Mediana" radius={[5, 5, 0, 0]} maxBarSize={70}>
              {item.groups.map((group) => <Cell key={group.state} fill={group.state === 'Sí cancela' ? '#e50914' : '#72727c'} />)}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      <div className="d-flex justify-content-between small text-secondary px-1">
        {item.groups.map((group) => <span key={group.state}>{group.state}: n={group.users.toLocaleString('es-PE')}</span>)}
      </div>
    </Panel>
  );
}
