import type { Quality } from '../api';
import Panel from '../components/Panel';
import { StateMessage } from '../components/StateMessage';

export default function QualityPage({ data }: { data: Quality | null }) {
  if (!data || data.status === 'pending') return <StateMessage kind="pending">{data?.message ?? 'Análisis pendiente. Ejecuta npm run analysis en la raíz.'}</StateMessage>;
  return (
    <div className="row g-3">
      <div className="col-12 col-md-6 col-xl-3">
        <div className="quality-stat"><span>Filas originales</span><strong>{data.original_rows?.toLocaleString('es-PE') ?? '—'}</strong></div>
      </div>
      <div className="col-12 col-md-6 col-xl-3">
        <div className="quality-stat"><span>Filas finales</span><strong>{data.final_rows?.toLocaleString('es-PE') ?? '—'}</strong></div>
      </div>
      <div className="col-12 col-md-6 col-xl-3">
        <div className="quality-stat"><span>Duplicados exactos retirados</span><strong>{data.exact_duplicates?.toLocaleString('es-PE') ?? '—'}</strong></div>
      </div>
      <div className="col-12 col-md-6 col-xl-3">
        <div className="quality-stat"><span>Incidencias auditadas</span><strong>{data.issue_incidences?.toLocaleString('es-PE') ?? '—'}</strong></div>
      </div>
      <div className="col-12">
        <Panel title="Decisiones de limpieza" description={data.counts_note}>
          {!data.audit_decisions?.length ? <StateMessage kind="empty">No hay decisiones auditadas.</StateMessage> : (
            <div className="table-responsive">
              <table className="table table-dark table-hover align-middle data-table mb-0">
                <thead><tr><th>Problema</th><th>Variable</th><th className="text-end">Registros por regla</th><th>Tratamiento</th><th>Justificación</th></tr></thead>
                <tbody>{data.audit_decisions.map((row, index) => <tr key={`${row.problema}-${row.variable}-${index}`}>
                  <th scope="row">{row.problema}</th><td>{row.variable}</td><td className="text-end">{Number(row.cantidad_registros_afectados).toLocaleString('es-PE')}</td>
                  <td>{row.tratamiento_aplicado}</td><td>{row.justificacion}</td>
                </tr>)}</tbody>
              </table>
            </div>
          )}
        </Panel>
      </div>
      <div className="col-12">
        <Panel title="Valores faltantes conservados" description="Los faltantes de predictores se imputan dentro del pipeline; no se eliminan filas automáticamente.">
          {!data.nulls_by_variable?.length ? <StateMessage kind="success">No hay valores faltantes en la tabla analítica limpia.</StateMessage> : (
            <div className="table-responsive">
              <table className="table table-dark table-hover align-middle data-table mb-0">
                <thead><tr><th>Variable</th><th className="text-end">Nulos</th><th className="text-end">Porcentaje de filas</th></tr></thead>
                <tbody>{data.nulls_by_variable.map((item) => <tr key={item.variable}><th scope="row">{item.variable}</th><td className="text-end">{item.count.toLocaleString('es-PE')}</td><td className="text-end">{(item.percent * 100).toFixed(2)}%</td></tr>)}</tbody>
              </table>
            </div>
          )}
        </Panel>
      </div>
    </div>
  );
}
