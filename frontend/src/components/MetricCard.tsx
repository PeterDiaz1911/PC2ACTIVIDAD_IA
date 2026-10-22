import type { LucideIcon } from 'lucide-react';

interface MetricCardProps {
  label: string;
  value: string;
  note: string;
  icon: LucideIcon;
  tone?: 'red' | 'neutral' | 'green';
}

export default function MetricCard({ label, value, note, icon: Icon, tone = 'neutral' }: MetricCardProps) {
  return (
    <article className={`metric-card metric-card--${tone} h-100`}>
      <div className="d-flex justify-content-between align-items-start gap-3">
        <div>
          <div className="metric-label">{label}</div>
          <div className="metric-value">{value}</div>
          <div className="metric-note">{note}</div>
        </div>
        <span className="metric-icon" aria-hidden="true"><Icon size={20} strokeWidth={1.8} /></span>
      </div>
    </article>
  );
}
