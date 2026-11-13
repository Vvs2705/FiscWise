/**
 * Hooks React da camada offline. As telas que escrevem nas entidades da seção
 * 3.1 devem usar `useLocalDb()` + `repositories.ts` (nunca api.post direto).
 */
import { useCallback, useMemo, useState } from 'react';
import { useLiveQuery } from 'dexie-react-hooks';
import { useAuthStore } from '@/stores/authStore';
import { getTenantId } from '@/lib/auth';
import { META, getMeta, openLocalDb, type FiscWiseLocalDb, type LocalConflict, type OutboxEvent } from './db';
import { decryptConflict, decryptEvent } from './fieldCrypto';
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
  return useLiveQuery(
    async () => (db ? Promise.all((await listUnsynced(db)).map((e) => decryptEvent(db, e))) : ([] as OutboxEvent[])),
    [db],
  );
}

/** Conflitos LWW ainda não revisados. */
export function useConflicts(): LocalConflict[] | undefined {
  const db = useLocalDb();
  return useLiveQuery(
    async () => {
      if (!db) return [] as LocalConflict[];
      const rows = await db.sync_conflicts.where('resolved').equals(0).reverse().sortBy('created_at');
      return Promise.all(rows.map((c) => decryptConflict(db, c)));
    },
    [db],
  );
}

export function useCurrentDeviceId(): string | undefined {
  const db = useLocalDb();
  return useLiveQuery(() => (db ? getMeta<string>(db, META.deviceId) : Promise.resolve(undefined)), [db]);
}

/** Aviso padrão dos botões que dependem do servidor (OFFLINE_SYNC.md, seções 3.3 e 8). */
export const OFFLINE_SERVER_NOTICE = 'Precisa de internet: esta ação depende do servidor.';
export const OFFLINE_FISCAL_NOTICE = 'Precisa de internet: a autorização depende da SEFAZ/prefeitura.';

/**
 * Guarda de ação que exige rede: `disabled` para compor com o disabled atual e
 * `title` com o aviso em português (undefined quando online).
 */
export function useOnlineOnly(notice: string = OFFLINE_SERVER_NOTICE) {
  const { isOffline } = useSyncStatus();
  return { isOffline, disabled: isOffline, title: isOffline ? notice : undefined };
}
