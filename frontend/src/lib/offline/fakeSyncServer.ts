/**
 * Servidor de sincronização falso para os testes (contrato de OFFLINE_SYNC.md 5.3/5.4):
 * idempotência por device_id:event_id, LWW por campo com version, pull por cursor.
 */
import { PULL_ENTITY, SyncNetworkError, type PullCursor, type PullEntity, type PushAck, type PushEvent, type SyncTransport } from './transport';
import type { SyncEntityType } from './db';

type Row = Record<string, unknown> & { id: string; version: number; updated_at: string };

const ENTITY_BY_PULL = Object.fromEntries(Object.entries(PULL_ENTITY).map(([k, v]) => [v, k])) as Record<PullEntity, SyncEntityType>;

export class FakeSyncServer {
  tables = new Map<SyncEntityType, Map<string, Row>>();
  processed = new Map<string, PushAck>();
  /** todos os eventos recebidos, inclusive reenvios */
  received: PushEvent[] = [];
  /** ids de eventos efetivamente aplicados (cada um uma vez) */
  applied: string[] = [];
  pushCalls: number[] = [];
  private clock = Date.parse('2026-01-01T00:00:00.000Z');

  private tick(): string {
    this.clock += 1000;
    return new Date(this.clock).toISOString();
  }

  table(entity: SyncEntityType): Map<string, Row> {
    let t = this.tables.get(entity);
    if (!t) {
      t = new Map();
      this.tables.set(entity, t);
    }
    return t;
  }

  /** escrita direta no servidor (outro canal: REST, scheduler) */
  seed(entity: SyncEntityType, row: Record<string, unknown> & { id: string }): Row {
    const full: Row = { version: 1, ...row, updated_at: this.tick() } as Row;
    this.table(entity).set(full.id, full);
    return full;
  }

  push(events: PushEvent[]): PushAck[] {
    this.pushCalls.push(events.length);
    return events.map((e) => {
      this.received.push(e);
      const key = `${e.device_id}:${e.id}`;
      const previous = this.processed.get(key);
      if (previous) return previous;
      const ack = this.apply(e);
      this.processed.set(key, ack);
      if (ack.status === 'ack') this.applied.push(e.id);
      return ack;
    });
  }

  private apply(e: PushEvent): PushAck {
    const t = this.table(e.entity_type);
    const row = t.get(e.entity_id);
    if (e.operation === 'create') {
      if (row) return { id: e.id, status: 'ack', entity: { ...row } };
      const created: Row = { ...e.payload, id: e.entity_id, version: 1, updated_at: this.tick() } as Row;
      t.set(created.id, created);
      return { id: e.id, status: 'ack', entity: { ...created } };
    }
    if (!row) return { id: e.id, status: 'rejected', error: 'Registro não encontrado.' };
    if (e.operation === 'emit_requested') {
      if (row.status === 'draft' || row.status === 'rejected') {
        row.status = 'queued';
        row.version += 1;
        row.updated_at = this.tick();
      }
      return { id: e.id, status: 'ack', entity: { ...row } };
    }
    if (typeof e.payload.status === 'string' && row.status === 'paid' && e.payload.status === 'pending') {
      return { id: e.id, status: 'rejected', error: 'Honorário pago não volta para pendente.' };
    }
    const conflict = e.base_version !== null && e.base_version < row.version;
    const fields: Record<string, { server: unknown; client: unknown }> = {};
    for (const [k, v] of Object.entries(e.payload)) {
      if (conflict && row[k] !== v) fields[k] = { server: row[k], client: v };
      row[k] = v;
    }
    row.version += 1;
    row.updated_at = this.tick();
    const hasConflict = conflict && Object.keys(fields).length > 0;
    return {
      id: e.id,
      status: 'ack',
      entity: { ...row },
      ...(hasConflict ? { conflict: true, fields_overwritten: fields } : {}),
    };
  }

  pull(entity: PullEntity, cursor: PullCursor, limit: number) {
    const rows = [...this.table(ENTITY_BY_PULL[entity]).values()]
      .sort((a, b) => (a.updated_at === b.updated_at ? a.id.localeCompare(b.id) : a.updated_at.localeCompare(b.updated_at)))
      .filter((r) => {
        if (!cursor.since) return true;
        if (r.updated_at > cursor.since) return true;
        return r.updated_at === cursor.since && !!cursor.after_id && r.id > cursor.after_id;
      });
    const page = rows.slice(0, limit).map((r) => ({ ...r }));
    const last = page[page.length - 1];
    return {
      rows: page,
      next: last ? { since: last.updated_at, after_id: last.id } : cursor,
      has_more: rows.length > limit,
    };
  }
}

export interface FakeTransportControls {
  offline: boolean;
  /** número da chamada de push (1-based) que perde a resposta depois de aplicar */
  dropResponseOnPushCall?: number;
  /** erro a lançar em toda chamada */
  throwError?: Error;
}

export function createFakeTransport(server: FakeSyncServer, controls: FakeTransportControls = { offline: false }): SyncTransport {
  let calls = 0;
  return {
    async push(events) {
      if (controls.throwError) throw controls.throwError;
      if (controls.offline) throw new SyncNetworkError();
      calls += 1;
      const acks = server.push(events);
      if (controls.dropResponseOnPushCall === calls) throw new SyncNetworkError('Conexão caiu durante o envio.');
      return acks;
    },
    async pull(entity, cursor, limit) {
      if (controls.throwError) throw controls.throwError;
      if (controls.offline) throw new SyncNetworkError();
      return server.pull(entity, cursor, limit);
    },
  };
}
