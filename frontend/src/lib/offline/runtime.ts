/**
 * Liga a camada offline à aplicação: abre o banco do escritório, garante o
 * dispositivo e registra os gatilhos do syncNow (OFFLINE_SYNC.md, seção 5.6):
 * abrir o app, evento `online`, a cada 60 s com rede, 2 s após enqueue, botão
 * manual e Background Sync (o SW só avisa as abas; a engine roda na aba).
 */
import { liveQuery } from 'dexie';
import { setAccessTokenRenewer } from '@/lib/api';
import {
  META,
  clearApiCache,
  getMeta,
  openLocalDb,
  setMeta,
  wipeLocalDb,
  type FiscWiseLocalDb,
  type SyncEntityType,
} from './db';
import { ensureDevice, getDeviceToken, renewAccessTokenWithDevice } from './device';
import { syncNow, type SyncResult } from './engine';
import { encryptExistingRows } from './fieldCrypto';
import { clearBackoff, countOutbox, onOutboxEnqueued } from './outbox';
import { useSyncStore } from './status';
import { DeviceRevokedError, createHttpTransport, httpDeviceApi, type SyncTransport } from './transport';

export const SYNC_INTERVAL_MS = 60_000;
export const ENQUEUE_DEBOUNCE_MS = 2_000;
export const BACKGROUND_SYNC_TAG = 'fiscwise-outbox';

interface ActiveRuntime {
  tenantId: string;
  db: FiscWiseLocalDb;
  transport: SyncTransport;
  run: () => Promise<SyncResult | null>;
}

let active: ActiveRuntime | null = null;

export function getActiveDb(): FiscWiseLocalDb | null {
  return active?.db ?? null;
}

/** Dispara um ciclo agora. `manual` libera os eventos em backoff. */
export async function requestSync(opts: { manual?: boolean } = {}): Promise<SyncResult | null> {
  if (!active) return null;
  if (opts.manual) await clearBackoff(active.db);
  return active.run();
}

export interface StartRuntimeOptions {
  tenantId: string;
  /** entidades alteradas localmente pela sincronização */
  onChanged?: (entities: Set<SyncEntityType>) => void;
}

async function handleRevoked(tenantId: string): Promise<void> {
  await Promise.all([wipeLocalDb(tenantId).catch(() => undefined), clearApiCache()]);
  localStorage.removeItem('access_token');
  localStorage.removeItem('tenant_id');
  localStorage.removeItem('user');
  window.location.href = '/login';
}

function registerBackgroundSync(): void {
  if (typeof navigator === 'undefined' || !('serviceWorker' in navigator)) return;
  navigator.serviceWorker.ready
    .then((reg) => {
      const sync = (reg as ServiceWorkerRegistration & { sync?: { register: (tag: string) => Promise<void> } }).sync;
      return sync?.register(BACKGROUND_SYNC_TAG);
    })
    .catch(() => undefined);
}

async function requestPersistentStorage(db: FiscWiseLocalDb): Promise<void> {
  try {
    if (await getMeta<boolean>(db, META.storagePersistRequested)) return;
    if (navigator.storage?.persist) {
      const persisted = await navigator.storage.persisted?.();
      if (!persisted) await navigator.storage.persist();
    }
    await setMeta(db, META.storagePersistRequested, true);
  } catch {
    // navegador sem StorageManager: segue sem persistência garantida
  }
}

/** Inicia a camada offline do escritório logado. Devolve a função de parada. */
export function startOfflineRuntime({ tenantId, onChanged }: StartRuntimeOptions): () => void {
  const db = openLocalDb(tenantId);
  const transport = createHttpTransport({ getDeviceToken: () => getDeviceToken(db), tenantId });
  const store = useSyncStore.getState();
  let stopped = false;

  const run = async (): Promise<SyncResult | null> => {
    if (stopped) return null;
    if (typeof navigator !== 'undefined' && navigator.onLine === false) {
      store.set({ networkUp: false, online: false, lastErrorKind: 'network', hasAttempted: true });
      return null;
    }
    try {
      const device = await ensureDevice(db, httpDeviceApi, { hasUserSession: !!localStorage.getItem('access_token') });
      if (device.accessToken) localStorage.setItem('access_token', device.accessToken);
      if (!device.deviceToken) {
        store.set({ online: false, lastError: 'Dispositivo ainda não registrado no servidor.', lastErrorKind: 'auth', hasAttempted: true });
        return null;
      }
    } catch (error) {
      if (error instanceof DeviceRevokedError) {
        await handleRevoked(tenantId);
        return null;
      }
      throw error;
    }
    return syncNow({ db, transport, onRevoked: () => handleRevoked(tenantId), onChanged });
  };

  active = { tenantId, db, transport, run };
  const safeRun = () => {
    void run().catch(() => undefined);
  };

  // Token comum vencido → renova pelo token de dispositivo antes de deslogar.
  setAccessTokenRenewer(() => renewAccessTokenWithDevice(db, httpDeviceApi));

  // Estado inicial vindo do banco local
  void getMeta<string>(db, META.lastSyncAt).then((at) => at && store.set({ lastSyncAt: at }));
  void requestPersistentStorage(db);
  // Bancos criados antes da criptografia de campos: cifra o que estiver em texto puro.
  void encryptExistingRows(db).catch(() => undefined);

  // Contadores sempre atualizados (inclusive alterações feitas em outra aba)
  const subscription = liveQuery(async () => {
    const counts = await countOutbox(db);
    const conflicts = await db.sync_conflicts.where('resolved').equals(0).count();
    return { ...counts, conflicts };
  }).subscribe({
    next: (v) => store.set({ pending: v.pending, errors: v.errors, conflicts: v.conflicts }),
    error: () => undefined,
  });

  // Gatilhos
  const onOnline = () => {
    store.set({ networkUp: true });
    safeRun();
  };
  const onOffline = () => store.set({ networkUp: false, online: false, lastErrorKind: 'network' });
  window.addEventListener('online', onOnline);
  window.addEventListener('offline', onOffline);

  const interval = window.setInterval(() => {
    if (navigator.onLine !== false) safeRun();
  }, SYNC_INTERVAL_MS);

  let debounce: number | undefined;
  const unsubscribeEnqueue = onOutboxEnqueued(() => {
    window.clearTimeout(debounce);
    debounce = window.setTimeout(safeRun, ENQUEUE_DEBOUNCE_MS);
    registerBackgroundSync();
  });

  const onSwMessage = (event: MessageEvent) => {
    if ((event.data as { type?: string } | null)?.type === 'fiscwise-sync') safeRun();
  };
  if ('serviceWorker' in navigator) navigator.serviceWorker.addEventListener('message', onSwMessage);

  safeRun();

  return () => {
    stopped = true;
    if (active?.db === db) active = null;
    setAccessTokenRenewer(null);
    subscription.unsubscribe();
    unsubscribeEnqueue();
    window.clearTimeout(debounce);
    window.clearInterval(interval);
    window.removeEventListener('online', onOnline);
    window.removeEventListener('offline', onOffline);
    if ('serviceWorker' in navigator) navigator.serviceWorker.removeEventListener('message', onSwMessage);
  };
}
