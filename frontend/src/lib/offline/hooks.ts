/**
 * Hooks React da camada offline. As telas que escrevem nas entidades da seção
 * 3.1 devem usar `useLocalDb()` + `repositories.ts` (nunca api.post direto).
 */
import { useCallback, useMemo, useState } from 'react';
import { useLiveQuery } from 'dexie-react-hooks';
import { useAuthStore } from '@/stores/authStore';
import { getTenantId } from '@/lib/auth';
import { META, getMeta, openLocalDb, type FiscWiseLocalDb, type LocalConflict, type OutboxEvent } from './db';
import { listUnsynced } from './outbox';
import { requestSync } from './runtime';
import { formatSyncIndicator, isEffectivelyOffline, syncIndicatorTone, useSyncStore } from './status';

export function useSyncStatus() {
  const state = useSyncStore();
  return useMemo(
    () => ({
      ...state,
      label: formatSyncIndicator(state),
      tone: syncIndicatorTone(state),
      isOffline: isEffectivelyOffline(state),
    }),
    [state],
  );
}

export function useSyncNow() {
  const [running, setRunning] = useState(false);
  const run = useCallback(async () => {
    setRunning(true);
    try {
      return await requestSync({ manual: true });
    } finally {
      setRunning(false);
    }
  }, []);
  return { syncNow: run, running };
}

/** Banco local do escritório logado (null fora de sessão ou no portal do cliente). */
export function useLocalDb(): FiscWiseLocalDb | null {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const role = useAuthStore((s) => s.user?.role);
  const tenantId = isAuthenticated && role !== 'client' ? getTenantId() : null;
  return useMemo(() => (tenantId ? openLocalDb(tenantId) : null), [tenantId]);
}

/** Eventos ainda não confirmados (pending, syncing, error), na ordem da fila. */
export function usePendingChanges(): OutboxEvent[] | undefined {
  const db = useLocalDb();
  return useLiveQuery(() => (db ? listUnsynced(db) : Promise.resolve([] as OutboxEvent[])), [db]);
}

/** Conflitos LWW ainda não revisados. */
export function useConflicts(): LocalConflict[] | undefined {
  const db = useLocalDb();
  return useLiveQuery(
    () => (db ? db.sync_conflicts.where('resolved').equals(0).reverse().sortBy('created_at') : Promise.resolve([] as LocalConflict[])),
    [db],
  );
}

export function useCurrentDeviceId(): string | undefined {
  const db = useLocalDb();
  return useLiveQuery(() => (db ? getMeta<string>(db, META.deviceId) : Promise.resolve(undefined)), [db]);
}
