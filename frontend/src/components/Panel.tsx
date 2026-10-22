import type { ReactNode } from 'react';

export default function Panel({ title, description, actions, children, className = '' }: {
  title: string;
  description?: string;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={`panel-card ${className}`}>
      <header className="panel-header">
        <div>
          <h2 className="panel-title">{title}</h2>
          {description && <p className="panel-description">{description}</p>}
        </div>
        {actions}
      </header>
      {children}
    </section>
  );
}
