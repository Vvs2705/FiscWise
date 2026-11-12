/**
 * Estado da sincronização para a UI (OFFLINE_SYNC.md, seção 8).
 * "Online" só depois de push/pull responderem, não só navigator.onLine (Moto-OS).
 */
import { create } from 'zustand';

export type SyncPhase = 'idle' | 'pushing' | 'pulling';
export type SyncErrorKind = 'network' | 'server' | 'auth' | null;

export interface SyncState {
  /** último push/pull respondeu */
  online: boolean;
  /** navigator.onLine (há interface de rede) */
  networkUp: boolean;
  phase: SyncPhase;
  /** eventos pending + syncing na outbox */
  pending: number;
  /** eventos rejeitados (status error) */
  errors: number;
  /** conflitos ainda não revisados */
  conflicts: number;
  batchTotal: number;
  batchDone: number;
  lastSyncAt: string | null;
  lastError: string | null;
  lastErrorKind: SyncErrorKind;
  /** algum ciclo já terminou nesta sessão (evita mostrar "Offline" no boot) */
  hasAttempted: boolean;
  set: (patch: Partial<Omit<SyncState, 'set'>>) => void;
}

const initialNetworkUp = typeof navigator === 'undefined' ? true : navigator.onLine !== false;

export const useSyncStore = create<SyncState>((set) => ({
  online: false,
  networkUp: initialNetworkUp,
  phase: 'idle',
  pending: 0,
  errors: 0,
  conflicts: 0,
  batchTotal: 0,
  batchDone: 0,
  lastSyncAt: null,
  lastError: null,
  lastErrorKind: null,
  hasAttempted: false,
  set: (patch) => set(patch),
}));

export type SyncIndicatorTone = 'online' | 'offline' | 'syncing' | 'error';

export type SyncIndicatorInput = Pick<
  SyncState,
  'online' | 'phase' | 'pending' | 'errors' | 'batchTotal' | 'batchDone'
> & Partial<Pick<SyncState, 'networkUp' | 'hasAttempted'>>;

export function syncIndicatorTone(s: SyncIndicatorInput): SyncIndicatorTone {
  if (s.errors > 0) return 'error';
  if (s.phase !== 'idle') return 'syncing';
  if (!s.online) return 'offline';
  return 'online';
}

/** Texto do indicador permanente: Online · Offline (N pendentes) · Sincronizando (x de y) · Erro (N itens). */
export function formatSyncIndicator(s: SyncIndicatorInput): string {
  const tone = syncIndicatorTone(s);
  if (tone === 'error') return `Erro (${s.errors} ${s.errors === 1 ? 'item' : 'itens'})`;
  if (tone === 'syncing') {
    const total = Math.max(s.batchTotal, s.batchDone);
    return `Sincronizando (${Math.min(s.batchDone, total)} de ${total})`;
  }
  if (tone === 'offline') return `Offline (${s.pending} ${s.pending === 1 ? 'pendente' : 'pendentes'})`;
  return 'Online';
}

/** Para telas que precisam decidir "sem internet" (emissão fiscal, cancelamento). */
export function isEffectivelyOffline(s: Pick<SyncState, 'networkUp' | 'lastErrorKind' | 'online'>): boolean {
  return !s.networkUp || (!s.online && s.lastErrorKind === 'network');
}
