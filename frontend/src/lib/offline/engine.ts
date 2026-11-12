/**
 * Ciclo de sincronização `syncNow` (OFFLINE_SYNC.md, seção 5.6):
 * recover → push em lotes de 200 → pull por entidade até has_more=false →
 * last_sync_at → avisa quem precisa invalidar o React Query.
 */
import {
  ENTITY_STORE,
  META,
  SYNC_ENTITIES,
  deleteMeta,
  getMeta,
  setMeta,
  type AnyLocalRow,
  type FiscWiseLocalDb,
  type OutboxEvent,
  type SyncEntityType,
} from './db';
import { getOrCreateDeviceId } from './device';
import {
  PUSH_BATCH_SIZE,
  countOutbox,
  enqueue,
  hasInFlightEvent,
  listPending,
  markAcked,
  markRejected,
  markSyncing,
  markTransportError,
  pruneSynced,
  recoverStuckOutbox,
} from './outbox';
import { useSyncStore, type SyncErrorKind } from './status';
import {
  DeviceAuthError,
  DeviceRevokedError,
  PULL_ENTITY,
  SyncNetworkError,
  TransientPushError,
  type PullCursor,
  type PushAck,
  type PushEvent,
  type SyncTransport,
} from './transport';

export const PULL_PAGE_SIZE = 500;

export interface SyncDeps {
  db: FiscWiseLocalDb;
  transport: SyncTransport;
  now?: () => Date;
  /** dispositivo revogado: apagar banco local e ir para o login */
  onRevoked?: () => void | Promise<void>;
  /** entidades que mudaram no banco local (para invalidar queries) */
  onChanged?: (entities: Set<SyncEntityType>) => void;
  /** atualiza o store Zustand (desligado nos testes que rodam em paralelo) */
  reportStatus?: boolean;
}

export interface SyncResult {
  status: 'ok' | 'offline' | 'error' | 'revoked' | 'skipped';
  pushed: number;
  acked: number;
  rejected: number;
  conflicts: number;
  pulled: number;
  error?: string;
}

// ─── Lock (mesma aba + entre abas via Web Locks) ─────────────────────────────

interface Running {
  promise: Promise<SyncResult>;
  again: boolean;
}
const running = new Map<string, Running>();

/**
 * Roda um ciclo. Se já houver um ciclo do mesmo banco em andamento, não abre
 * outro: marca para rodar de novo ao final (pega o que foi enfileirado no meio)
 * e devolve a promessa do ciclo atual.
 */
export function syncNow(deps: SyncDeps): Promise<SyncResult> {
  const key = deps.db.name;
  const current = running.get(key);
  if (current) {
    current.again = true;
    return current.promise;
  }
  const entry: Running = { promise: Promise.resolve(emptyResult('skipped')), again: false };
  entry.promise = (async () => {
    try {
      let result: SyncResult;
      do {
        entry.again = false;
        result = await withCrossTabLock(key, () => runCycle(deps));
      } while (entry.again && result.status === 'ok');
      return result;
    } finally {
      running.delete(key);
    }
  })();
  running.set(key, entry);
  return entry.promise;
}

async function withCrossTabLock<T>(name: string, fn: () => Promise<T>): Promise<T> {
  const locks = typeof navigator !== 'undefined' ? (navigator as Navigator & { locks?: LockManager }).locks : undefined;
  if (!locks?.request) return fn();
  return locks.request(`fiscwise-sync:${name}`, () => fn()) as Promise<T>;
}

function emptyResult(status: SyncResult['status']): SyncResult {
  return { status, pushed: 0, acked: 0, rejected: 0, conflicts: 0, pulled: 0 };
}

// ─── Ciclo ───────────────────────────────────────────────────────────────────

async function runCycle(deps: SyncDeps): Promise<SyncResult> {
  const { db, transport } = deps;
  const now = deps.now ?? (() => new Date());
  const report = deps.reportStatus !== false;
  const setStatus = (patch: Parameters<ReturnType<typeof useSyncStore.getState>['set']>[0]) => {
    if (report) useSyncStore.getState().set(patch);
  };
  const result = emptyResult('ok');
  const changed = new Set<SyncEntityType>();

  try {
    // 1. eventos presos em syncing voltam para pending
    await recoverStuckOutbox(db);
    const deviceId = await getOrCreateDeviceId(db);

    // 2. push em lotes de 200
    const startCounts = await countOutbox(db);
    setStatus({ phase: 'pushing', batchTotal: startCounts.pending, batchDone: 0 });
    const pushOutcome = await pushAll(deps, deviceId, now, (done) => setStatus({ batchDone: done }), changed, result);
    if (pushOutcome) throw pushOutcome;

    // 3. pull de cada entidade até has_more=false
    setStatus({ phase: 'pulling', batchTotal: SYNC_ENTITIES.length, batchDone: 0 });
    let step = 0;
    for (const entity of SYNC_ENTITIES) {
      result.pulled += await pullEntity(db, transport, entity, changed);
      step += 1;
      setStatus({ batchDone: step });
    }

    // 4. last_sync_at
    const at = now().toISOString();
    await setMeta(db, META.lastSyncAt, at);
    await deleteMeta(db, META.lastError);
    await pruneSynced(db, now());
    setStatus({ online: true, lastSyncAt: at, lastError: null, lastErrorKind: null });
    return result;
  } catch (error) {
    if (error instanceof DeviceRevokedError) {
      setStatus({ online: false, lastError: error.message, lastErrorKind: 'auth' });
      await deps.onRevoked?.();
      return { ...result, status: 'revoked', error: error.message };
    }
    const kind: SyncErrorKind =
      error instanceof SyncNetworkError ? 'network' : error instanceof DeviceAuthError ? 'auth' : 'server';
    if (error instanceof DeviceAuthError) await deleteMeta(db, META.deviceToken);
    const message = error instanceof Error ? error.message : String(error);
    await setMeta(db, META.lastError, message).catch(() => undefined);
    setStatus({ online: false, lastError: message, lastErrorKind: kind });
    return { ...result, status: kind === 'network' ? 'offline' : 'error', error: message };
  } finally {
    setStatus({ phase: 'idle', hasAttempted: true });
    if (report) {
      const counts = await countOutbox(db).catch(() => null);
      const conflicts = await db.sync_conflicts.where('resolved').equals(0).count().catch(() => 0);
      if (counts) setStatus({ pending: counts.pending, errors: counts.errors, conflicts });
    }
    if (changed.size > 0) deps.onChanged?.(changed);
  }
}

function toPushEvent(e: OutboxEvent, deviceId: string): PushEvent {
  return {
    id: e.id,
    device_id: deviceId,
    entity_type: e.entity_type,
    entity_id: e.entity_id,
    operation: e.operation,
    payload: e.payload,
    base_version: e.base_version,
    created_at: e.created_at,
  };
}

/** Drena a outbox. Devolve o erro que interrompeu o push (ou null). */
async function pushAll(
  deps: SyncDeps,
  deviceId: string,
  now: () => Date,
  progress: (done: number) => void,
  changed: Set<SyncEntityType>,
  result: SyncResult,
): Promise<Error | null> {
  const { db, transport } = deps;
  let done = 0;
  // Teto de segurança: nunca mais lotes do que a fila comporta.
  for (let guard = 0; guard < 10_000; guard += 1) {
    const batch = await listPending(db, now(), PUSH_BATCH_SIZE);
    if (batch.length === 0) return null;
    const ids = batch.map((e) => e.id);
    await markSyncing(db, ids);
    result.pushed += batch.length;

    let acks: PushAck[];
    let interruption: Error | null = null;
    try {
      acks = await transport.push(batch.map((e) => toPushEvent(e, deviceId)));
    } catch (error) {
      if (error instanceof DeviceRevokedError) throw error;
      if (error instanceof TransientPushError) {
        acks = error.acks;
        interruption = error;
      } else {
        const err = error instanceof Error ? error : new Error(String(error));
        await markTransportError(db, ids, err.message, now());
        return err;
      }
    }

    const ackById = new Map(acks.map((a) => [a.id, a]));
    const missing: string[] = [];
    for (const event of batch) {
      const ack = ackById.get(event.id);
      if (!ack) {
        missing.push(event.id);
        continue;
      }
      await applyAck(db, event, ack, now());
      changed.add(event.entity_type);
      if (ack.status === 'ack') result.acked += 1;
      else result.rejected += 1;
      if (ack.conflict) result.conflicts += 1;
      done += 1;
    }
    progress(done);
    if (missing.length > 0) {
      const message = interruption?.message ?? 'Servidor não confirmou o recebimento.';
      await markTransportError(db, missing, message, now());
      return interruption ?? new Error(message);
    }
    if (interruption) return interruption;
  }
  return null;
}

async function applyAck(db: FiscWiseLocalDb, event: OutboxEvent, ack: PushAck, now: Date): Promise<void> {
  const table = db.entityTable(event.entity_type);
  await db.transaction('rw', [table, db.sync_outbox, db.sync_conflicts], async () => {
    if (ack.status === 'rejected') {
      const reason = ack.error?.trim() || 'Rejeitado pelo servidor.';
      await markRejected(db, event.id, reason);
      const row = await table.get(event.entity_id);
      if (row) await table.put({ ...row, _sync_status: 'error', _sync_error: reason });
      return;
    }
    await markAcked(db, event.id, now);
    const stillLocal = await hasInFlightEvent(db, event.entity_type, event.entity_id, event.id);
    const row = await table.get(event.entity_id);
    const server = ack.entity && typeof ack.entity === 'object' ? (ack.entity as Partial<AnyLocalRow>) : null;
    if (server) {
      await table.put(mergeServerRow(row, server as AnyLocalRow, stillLocal));
    } else if (row && !stillLocal) {
      await table.put({ ...row, _sync_status: 'synced', _sync_error: null });
    }
    if (ack.conflict && ack.fields_overwritten && Object.keys(ack.fields_overwritten).length > 0) {
      await db.sync_conflicts.put({
        id: event.id,
        entity_type: event.entity_type,
        entity_id: event.entity_id,
        fields_overwritten: ack.fields_overwritten,
        created_at: now.toISOString(),
        resolved_at: null,
        resolved: 0,
      });
    }
  });
}

/**
 * Linha do servidor sempre vence, exceto quando há edição local em voo para o
 * mesmo registro: aí só a `version` base é atualizada e a edição local fica.
 */
function mergeServerRow(local: AnyLocalRow | undefined, server: AnyLocalRow, keepLocal: boolean): AnyLocalRow {
  if (keepLocal && local) {
    return { ...local, version: typeof server.version === 'number' ? server.version : local.version };
  }
  return {
    ...server,
    version: typeof server.version === 'number' ? server.version : (local?.version ?? 1),
    _sync_status: 'synced',
    _sync_error: null,
    _local_updated_at: null,
  };
}

async function pullEntity(
  db: FiscWiseLocalDb,
  transport: SyncTransport,
  entity: SyncEntityType,
  changed: Set<SyncEntityType>,
): Promise<number> {
  const table = db.entityTable(entity);
  const cursorKey = META.cursor(entity);
  let cursor: PullCursor = (await getMeta<PullCursor>(db, cursorKey)) ?? { since: null, after_id: null };
  let total = 0;
  for (let guard = 0; guard < 100_000; guard += 1) {
    const page = await transport.pull(PULL_ENTITY[entity], cursor, PULL_PAGE_SIZE);
    const rows = page.rows ?? [];
    const next = page.next ?? cursor;
    // Grava todas as linhas do lote e só então persiste o cursor (mesma transação).
    await db.transaction('rw', [table, db.sync_outbox, db.sync_meta], async () => {
      for (const serverRow of rows) {
        const inFlight = await hasInFlightEvent(db, entity, serverRow.id);
        const local = await table.get(serverRow.id);
        await table.put(mergeServerRow(local, serverRow as AnyLocalRow, inFlight));
      }
      await setMeta(db, cursorKey, next);
    });
    total += rows.length;
    if (rows.length > 0) changed.add(entity);
    const advanced = next.since !== cursor.since || next.after_id !== cursor.after_id;
    cursor = next;
    if (!page.has_more || !advanced) break;
  }
  return total;
}

// ─── Ações da tela de sincronização ──────────────────────────────────────────

/**
 * Descarta um evento rejeitado. A versão do servidor volta no próximo pull
 * (o cursor da entidade é zerado para rebaixar as linhas dela).
 */
export async function discardEvent(db: FiscWiseLocalDb, eventId: string): Promise<void> {
  await db.transaction('rw', [db.sync_outbox, db.sync_meta, ...Object.values(ENTITY_STORE).map((s) => db.table(s))], async () => {
    const event = await db.sync_outbox.get(eventId);
    if (!event) return;
    await db.sync_outbox.delete(eventId);
    const table = db.entityTable(event.entity_type);
    const others = await db.sync_outbox
      .where('[entity_type+entity_id]')
      .equals([event.entity_type, event.entity_id])
      .filter((e) => e.status !== 'synced')
      .count();
    if (others === 0) {
      if (event.operation === 'create') await table.delete(event.entity_id);
      await deleteMeta(db, META.cursor(event.entity_type));
    }
  });
}

/** "Manter como está": marca o conflito como revisado. */
export async function resolveConflictKeep(db: FiscWiseLocalDb, conflictId: string): Promise<void> {
  await db.sync_conflicts.update(conflictId, { resolved: 1, resolved_at: new Date().toISOString() });
}

/** "Restaurar valor do servidor": gera um novo update com os valores anteriores do servidor. */
export async function resolveConflictRestoreServer(db: FiscWiseLocalDb, conflictId: string): Promise<void> {
  const conflict = await db.sync_conflicts.get(conflictId);
  if (!conflict) return;
  const patch = Object.fromEntries(Object.entries(conflict.fields_overwritten).map(([field, v]) => [field, v.server]));
  const table = db.entityTable(conflict.entity_type);
  await db.transaction('rw', [table, db.sync_outbox, db.sync_conflicts], async () => {
    const row = await table.get(conflict.entity_id);
    if (row) {
      const ts = new Date().toISOString();
      await table.put({ ...row, ...patch, updated_at: ts, _sync_status: 'pending', _local_updated_at: ts });
    }
    await enqueue(db, {
      entity_type: conflict.entity_type,
      entity_id: conflict.entity_id,
      operation: 'update',
      payload: patch,
      base_version: row?.version ?? null,
    });
    await db.sync_conflicts.update(conflictId, { resolved: 1, resolved_at: new Date().toISOString() });
  });
}
