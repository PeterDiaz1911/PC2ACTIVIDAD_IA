import { AlertCircle, CheckCircle2, Database, LoaderCircle } from 'lucide-react';

export function StateMessage({ kind, children }: { kind: 'loading' | 'error' | 'empty' | 'pending' | 'success'; children: string }) {
  const Icon = kind === 'loading' ? LoaderCircle : kind === 'error' ? AlertCircle : kind === 'success' ? CheckCircle2 : Database;
  return (
    <div className={`state-message state-message--${kind}`} role={kind === 'error' ? 'alert' : 'status'}>
      <Icon size={19} aria-hidden="true" className={kind === 'loading' ? 'spin' : ''} />
      <span>{children}</span>
    </div>
  );
}
