import { Link } from 'react-router-dom';
import { AlertTriangle, Cloud, CloudOff, RefreshCw } from 'lucide-react';
import { useSyncStatus } from '@/lib/offline/hooks';
import { cn } from '@/lib/utils';

const TONE_CLASSES = {
  online: 'border-success/30 bg-success/10 text-success',
  offline: 'border-muted-foreground/30 bg-muted text-muted-foreground',
  syncing: 'border-info/30 bg-info/10 text-info',
  error: 'border-destructive/30 bg-destructive/10 text-destructive',
} as const;

const TONE_ICON = {
  online: Cloud,
  offline: CloudOff,
  syncing: RefreshCw,
  error: AlertTriangle,
} as const;

/**
 * Indicador permanente de sincronização (OFFLINE_SYNC.md, seção 8).
 * Visível em todas as larguras; no celular mostra só o ícone e o número.
 */
export function SyncIndicator() {
  const status = useSyncStatus();
  // Antes do primeiro ciclo terminar, não acusar "Offline" sem motivo.
  const tone = !status.hasAttempted && status.tone === 'offline' && status.networkUp ? 'syncing' : status.tone;
  const label = tone === 'syncing' && !status.hasAttempted ? 'Conectando…' : status.label;
  const Icon = TONE_ICON[tone];
  const count = tone === 'error' ? status.errors : tone === 'offline' ? status.pending : 0;

  return (
    <Link
      to="/sincronizacao"
      role="status"
      aria-live="polite"
      aria-label={`Sincronização: ${label}. Abrir detalhes da sincronização.`}
      title={status.lastError && tone !== 'online' ? `${label} — ${status.lastError}` : label}
      className={cn(
        'inline-flex h-9 shrink-0 items-center gap-1.5 rounded-full border px-2.5 text-xs font-semibold',
        'transition-colors hover:opacity-90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
        TONE_CLASSES[tone],
      )}
    >
      <Icon className={cn('h-3.5 w-3.5 shrink-0', tone === 'syncing' && 'animate-spin')} aria-hidden="true" />
      <span className="hidden whitespace-nowrap sm:inline">{label}</span>
      {count > 0 && (
        <span className="sm:hidden" aria-hidden="true">
          {count}
        </span>
      )}
    </Link>
  );
}
