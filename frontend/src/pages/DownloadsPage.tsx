import { Download, FileChartColumn, FileSpreadsheet, FileText, Presentation } from 'lucide-react';
import type { DownloadItem } from '../api';
import { downloadUrl } from '../api';
import Panel from '../components/Panel';
import { StateMessage } from '../components/StateMessage';

const fileIcons: Record<string, typeof Download> = {
  'presentacion_netflix.pptx': Presentation,
  'netflix_limpio.csv': FileSpreadsheet,
  'metricas_modelos.csv': FileChartColumn,
  'evaluation_netflix.json': FileText,
};

export default function DownloadsPage({ items, error }: { items: DownloadItem[]; error?: string }) {
  if (error) return <StateMessage kind="error">{error}</StateMessage>;
  return (
    <Panel title="Resultados y descargas" description="Solo se ofrecen artefactos de resultados definidos por una lista autorizada; no se admiten rutas del equipo.">
      {!items.length ? <StateMessage kind="pending">No hay resultados publicados aún. Ejecuta npm run analysis desde la raíz para generarlos.</StateMessage> : (
        <div className="row g-3">
          {items.map((item) => {
            const Icon = fileIcons[item.filename] ?? FileText;
            return <div className="col-12 col-md-6 col-xl-4" key={item.id}>
              <article className={`download-card ${item.available ? '' : 'download-card--disabled'}`}>
                <span className="download-icon"><Icon size={22} /></span>
                <div className="flex-grow-1 min-w-0">
                  <h3>{item.filename}</h3>
                  <p>{item.available ? 'Resultado generado' : 'Análisis pendiente'}</p>
                </div>
                {item.available
                  ? <a className="download-link" href={downloadUrl(item.id)} aria-label={`Descargar ${item.filename}`}><Download size={18} /></a>
                  : <span className="text-secondary small">Pendiente</span>}
              </article>
            </div>;
          })}
        </div>
      )}
    </Panel>
  );
}
