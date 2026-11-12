import { AlertTriangle } from 'lucide-react';
import type { LocalSyncStatus } from '@/lib/offline/db';

interface SyncRowMarkerProps {
  status?: LocalSyncStatus | null;
  error?: string | null;
  className?: string;
}

/**
 * Marcador por linha (OFFLINE_SYNC.md, seção 8): ponto discreto quando a
 * alteração ainda não foi enviada; alerta com o motivo quando o servidor recusou.
 */
export function SyncRowMarker({ status, error, className = '' }: SyncRowMarkerProps) {
  if (status === 'pending') {
    return (
      <span
        role="img"
        aria-label="Não enviado ainda"
        title="Não enviado ainda"
        className={`inline-block h-1.5 w-1.5 shrink-0 rounded-full bg-warning align-middle ${className}`}
      />
    );
  }
  if (status === 'error') {
    const reason = error?.trim() || 'Rejeitado pelo servidor.';
    return (
      <span role="img" aria-label={`Não sincronizado: ${reason}`} title={`Não sincronizado: ${reason}`} className={`inline-flex shrink-0 align-middle ${className}`}>
        <AlertTriangle className="h-3.5 w-3.5 text-destructive" aria-hidden="true" />
      </span>
    );
  }
  return null;
}
