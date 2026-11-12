/**
 * Outbox local (OFFLINE_SYNC.md, seção 5.2). Padrões do Moto-OS:
 * SYNCING antes do envio, SYNCED só após ACK, recoverStuckOutbox na abertura,
 * backoff exponencial 5 s → 10 min em erro de transporte.
 */
import type { FiscWiseLocalDb, OutboxEvent, SyncEntityType, SyncOperation } from './db';

export type { OutboxEvent, OutboxStatus, SyncEntityType, SyncOperation } from './db';

export interface EnqueueInput {
  entity_type: SyncEntityType;
  entity_id: string;
  operation: SyncOperation;
  payload: Record<string, unknown>;
  base_version: number | null;
}

export const PUSH_BATCH_SIZE = 200;

/** 5 s, 10 s, 20 s ... limitado a 10 min. */
export function outboxBackoffMs(attempts: number): number {
  return Math.min(5_000 * 2 ** Math.max(0, attempts - 1), 600_000);
}

type EnqueueListener = (event: OutboxEvent) => void;
const enqueueListeners = new Set<EnqueueListener>();

/** Gatilho "debounce 2 s após enqueue" e Background Sync se registram aqui. */
export function onOutboxEnqueued(listener: EnqueueListener): () => void {
  enqueueListeners.add(listener);
  return () => enqueueListeners.delete(listener);
}

function newId(): string {
  return globalThis.crypto.randomUUID();
}

/**
 * Grava um evento na outbox. Chamar dentro da mesma transação Dexie que grava a
 * linha da entidade (a transação externa precisa incluir `sync_outbox`).
 *
 * Coalescência: um `update` de um registro que já tem evento `pending`
 * (create ou update, ainda não enviado) é mesclado nele — payload mesclado,
 * `base_version` do primeiro, posição na fila do primeiro.
 */
export async function enqueue(db: FiscWiseLocalDb, input: EnqueueInput, now: Date = new Date()): Promise<OutboxEvent> {
  const event = await db.transaction('rw', db.sync_outbox, async () => {
    if (input.operation === 'update') {
      const same = await db.sync_outbox
        .where('[entity_type+entity_id]')
        .equals([input.entity_type, input.entity_id])
        .toArray();
      const target = same
        .filter((e) => e.status === 'pending' && (e.operation === 'update' || e.operation === 'create'))
        .sort((a, b) => b.seq - a.seq)[0];
      // Só coalesce com o último evento do registro: se depois dele veio um
      // delete/emit_requested, a ordem importa e o update vira evento novo.
      const last = same.sort((a, b) => b.seq - a.seq)[0];
      if (target && last && target.id === last.id) {
        const merged: OutboxEvent = { ...target, payload: { ...target.payload, ...input.payload } };
        await db.sync_outbox.put(merged);
        return merged;
      }
    }
    const lastSeq = (await db.sync_outbox.orderBy('seq').last())?.seq ?? 0;
    const created: OutboxEvent = {
      id: newId(),
      seq: lastSeq + 1,
      entity_type: input.entity_type,
      entity_id: input.entity_id,
      operation: input.operation,
      payload: input.payload,
      base_version: input.base_version,
      created_at: now.toISOString(),
      attempts: 0,
      status: 'pending',
      last_error: null,
      next_retry_at: null,
      synced_at: null,
    };
    await db.sync_outbox.add(created);
    return created;
  });
  for (const listener of enqueueListeners) {
    try {
      listener(event);
    } catch {
      // listener de UI nunca derruba a escrita local
    }
  }
  return event;
}

/** Eventos prontos para envio, na ordem de criação. */
export async function listPending(db: FiscWiseLocalDb, now: Date = new Date(), limit = PUSH_BATCH_SIZE): Promise<OutboxEvent[]> {
  const nowIso = now.toISOString();
  const rows = await db.sync_outbox.where('status').equals('pending').sortBy('seq');
  return rows.filter((e) => !e.next_retry_at || e.next_retry_at <= nowIso).slice(0, limit);
}

/** Pendências visíveis ao usuário (pending + syncing + error), na ordem de criação. */
export async function listUnsynced(db: FiscWiseLocalDb): Promise<OutboxEvent[]> {
  const rows = await db.sync_outbox.where('status').anyOf('pending', 'syncing', 'error').toArray();
  return rows.sort((a, b) => a.seq - b.seq);
}

/**
 * Devolve à fila os eventos presos em `syncing` (aba fechada no meio do envio).
 * Reenviar é seguro: o servidor deduplica por `device_id:event_id`.
 */
export async function recoverStuckOutbox(db: FiscWiseLocalDb): Promise<number> {
  return db.sync_outbox.where('status').equals('syncing').modify({ status: 'pending' });
}

export async function markSyncing(db: FiscWiseLocalDb, ids: string[]): Promise<void> {
  await db.sync_outbox.where('id').anyOf(ids).modify({ status: 'syncing' });
}

export async function markAcked(db: FiscWiseLocalDb, id: string, now: Date = new Date()): Promise<void> {
  await db.sync_outbox.where('id').equals(id).modify((e) => {
    e.status = 'synced';
    e.synced_at = now.toISOString();
    e.attempts += 1;
    e.last_error = null;
    e.next_retry_at = null;
  });
}

/** Rejeição do servidor: não entra em retry, fica `error` com o motivo até o usuário agir. */
export async function markRejected(db: FiscWiseLocalDb, id: string, error: string): Promise<void> {
  await db.sync_outbox.where('id').equals(id).modify((e) => {
    e.status = 'error';
    e.attempts += 1;
    e.last_error = error;
    e.next_retry_at = null;
  });
}

/** Erro de transporte: volta a `pending` com backoff exponencial. */
export async function markTransportError(db: FiscWiseLocalDb, ids: string[], message: string, now: Date = new Date()): Promise<void> {
  if (ids.length === 0) return;
  await db.sync_outbox.where('id').anyOf(ids).modify((e) => {
    e.status = 'pending';
    e.attempts += 1;
    e.last_error = message;
    e.next_retry_at = new Date(now.getTime() + outboxBackoffMs(e.attempts)).toISOString();
  });
}

/** Ação do usuário na tela de sincronização: tentar de novo um evento rejeitado. */
export async function retryEvent(db: FiscWiseLocalDb, id: string): Promise<void> {
  await db.sync_outbox.where('id').equals(id).modify((e) => {
    e.status = 'pending';
    e.next_retry_at = null;
  });
}

/** Libera todos os eventos em backoff para o próximo ciclo (botão "Sincronizar agora"). */
export async function clearBackoff(db: FiscWiseLocalDb): Promise<void> {
  await db.sync_outbox.where('status').equals('pending').modify({ next_retry_at: null });
}

/** Remove eventos já confirmados há mais de `maxAgeMs` (o histórico fica no servidor). */
export async function pruneSynced(db: FiscWiseLocalDb, now: Date = new Date(), maxAgeMs = 24 * 60 * 60 * 1000): Promise<number> {
  const cutoff = new Date(now.getTime() - maxAgeMs).toISOString();
  return db.sync_outbox
    .where('status')
    .equals('synced')
    .filter((e) => !!e.synced_at && e.synced_at < cutoff)
    .delete();
}

/** Há edição local ainda não confirmada para o registro? (pending ou syncing) */
export async function hasInFlightEvent(
  db: FiscWiseLocalDb,
  entity: SyncEntityType,
  entityId: string,
  exceptId?: string,
): Promise<boolean> {
  const n = await db.sync_outbox
    .where('[entity_type+entity_id]')
    .equals([entity, entityId])
    .filter((e) => e.id !== exceptId && (e.status === 'pending' || e.status === 'syncing'))
    .count();
  return n > 0;
}

export interface OutboxCounts {
  pending: number;
  errors: number;
}

export async function countOutbox(db: FiscWiseLocalDb): Promise<OutboxCounts> {
  const [pending, syncing, errors] = await Promise.all([
    db.sync_outbox.where('status').equals('pending').count(),
    db.sync_outbox.where('status').equals('syncing').count(),
    db.sync_outbox.where('status').equals('error').count(),
  ]);
  return { pending: pending + syncing, errors };
}
