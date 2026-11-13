import { describe, expect, it } from 'vitest';
import Dexie from 'dexie';
import { FiscWiseLocalDb, META, getMeta, openLocalDb, setMeta, wipeLocalDb } from './db';
import { discardEvent, resolveConflictRestoreServer, syncNow, type SyncDeps } from './engine';
import { decryptEvent } from './fieldCrypto';
import { createFakeTransport, FakeSyncServer, type FakeTransportControls } from './fakeSyncServer';
import { enqueue, listPending, markSyncing, outboxBackoffMs, recoverStuckOutbox } from './outbox';
import {
  createClient,
  createInvoiceDraft,
  createReceivable,
  deactivateClient,
  listClients,
  markReceivablePaid,
  requestInvoiceEmission,
  updateClient,
} from './repositories';
import { DeviceRevokedError } from './transport';

let counter = 0;
function freshDb(): FiscWiseLocalDb {
  counter += 1;
  return new FiscWiseLocalDb(`tenant-${counter}`, `fiscwise-test-${counter}-${Math.random().toString(36).slice(2)}`);
}

function deps(db: FiscWiseLocalDb, server: FakeSyncServer, controls: FakeTransportControls = { offline: false }, extra: Partial<SyncDeps> = {}): SyncDeps {
  return { db, transport: createFakeTransport(server, controls), reportStatus: false, ...extra };
}

const clientData = (name: string) => ({ name, entity_type: 'pj' as const, status: 'active' as const });

/** "agora" bem depois de qualquer backoff */
const later = () => new Date(Date.now() + 60 * 60 * 1000);

describe('cenário 1: offline → cria/edita → online → sincroniza', () => {
  it('envia as alterações, esvazia a outbox e grava a version do servidor', async () => {
    const db = freshDb();
    const server = new FakeSyncServer();
    const controls: FakeTransportControls = { offline: true };

    const created = await createClient(db, clientData('Padaria Sol'));
    await updateClient(db, created.id, { email: 'contato@sol.com.br' });
    expect((await db.clients.get(created.id))?._sync_status).toBe('pending');

    const offlineRun = await syncNow(deps(db, server, controls));
    expect(offlineRun.status).toBe('offline');
    // create + update coalescidos em um único evento ainda pendente
    expect(await db.sync_outbox.where('status').equals('pending').count()).toBe(1);
    expect((await listClients(db)).map((c) => c.name)).toEqual(['Padaria Sol']);

    controls.offline = false;
    const res = await syncNow({ ...deps(db, server, controls), now: later });
    expect(res.status).toBe('ok');
    expect(await db.sync_outbox.where('status').anyOf('pending', 'syncing', 'error').count()).toBe(0);
    const serverRow = server.table('client').get(created.id)!;
    expect(serverRow.email).toBe('contato@sol.com.br');

    // edição offline de registro já sincronizado: version sobe para a do servidor
    controls.offline = true;
    await updateClient(db, created.id, { phone: '11999990000' });
    await syncNow(deps(db, server, controls));
    controls.offline = false;
    await syncNow({ ...deps(db, server, controls), now: later });
    const local = await db.clients.get(created.id);
    expect(local?.version).toBe(2);
    expect(local?.version).toBe(server.table('client').get(created.id)!.version);
    expect(local?._sync_status).toBe('synced');
    expect(await getMeta(db, META.lastSyncAt)).toBeTruthy();
  });

  it('pull traz escrita feita por outro canal; linha com edição pendente mantém o valor local', async () => {
    const db = freshDb();
    const server = new FakeSyncServer();
    const a = server.seed('client', { id: 'c-1', name: 'Original', status: 'active' });
    await syncNow(deps(db, server));
    expect((await db.clients.get('c-1'))?.name).toBe('Original');

    // edição local ainda pendente (em backoff, não sobe neste ciclo) + servidor muda a linha
    const ev = await updateClient(db, 'c-1', { name: 'Local' }).then(() => db.sync_outbox.toArray());
    await db.sync_outbox.update(ev[0].id, { next_retry_at: '2999-01-01T00:00:00.000Z' });
    a.name = 'Servidor';
    a.version = 2;
    a.updated_at = '2027-01-01T00:00:00.000Z';
    await syncNow(deps(db, server));
    let local = await db.clients.get('c-1');
    expect(local?.name).toBe('Local');
    expect(local?.version).toBe(2);
    expect(local?._sync_status).toBe('pending');

    // sem edição pendente, a linha do servidor vence
    await db.sync_outbox.clear();
    a.name = 'Servidor 2';
    a.version = 3;
    a.updated_at = '2027-01-02T00:00:00.000Z';
    await syncNow(deps(db, server));
    local = await db.clients.get('c-1');
    expect(local?.name).toBe('Servidor 2');
    expect(local?._sync_status).toBe('synced');
  });
});

describe('cenário 2: conflito entre dois device_ids', () => {
  it('o segundo recebe conflito e a revisão mostra os campos', async () => {
    const server = new FakeSyncServer();
    server.seed('client', { id: 'c-9', name: 'Mercado Azul', status: 'active' });
    const dbA = freshDb();
    const dbB = freshDb();
    await syncNow(deps(dbA, server));
    await syncNow(deps(dbB, server));
    const idA = await getMeta<string>(dbA, META.deviceId);
    const idB = await getMeta<string>(dbB, META.deviceId);
    expect(idA).toBeTruthy();
    expect(idA).not.toBe(idB);

    await updateClient(dbA, 'c-9', { name: 'Mercado Azul Ltda' });
    await syncNow(deps(dbA, server));
    await updateClient(dbB, 'c-9', { name: 'Mercado Azul ME' });
    const res = await syncNow(deps(dbB, server));
    expect(res.conflicts).toBe(1);

    const conflicts = await dbB.sync_conflicts.where('resolved').equals(0).toArray();
    expect(conflicts).toHaveLength(1);
    expect(conflicts[0].fields_overwritten).toEqual({ name: { server: 'Mercado Azul Ltda', client: 'Mercado Azul ME' } });
    expect(server.table('client').get('c-9')!.name).toBe('Mercado Azul ME');
    expect(await dbA.sync_conflicts.count()).toBe(0);

    // "Restaurar valor do servidor" gera um novo update
    await resolveConflictRestoreServer(dbB, conflicts[0].id);
    expect(await dbB.sync_conflicts.where('resolved').equals(0).count()).toBe(0);
    await syncNow(deps(dbB, server));
    expect(server.table('client').get('c-9')!.name).toBe('Mercado Azul Ltda');
  });
});

describe('cenário 3: queda no meio do push', () => {
  it('retomada não duplica (ACK idempotente do servidor)', async () => {
    const db = freshDb();
    const server = new FakeSyncServer();
    for (let i = 0; i < 450; i += 1) await createClient(db, clientData(`Cliente ${String(i).padStart(3, '0')}`));

    // lote 2 chega ao servidor, é aplicado, mas a resposta se perde
    const controls: FakeTransportControls = { offline: false, dropResponseOnPushCall: 2 };
    const first = await syncNow(deps(db, server, controls));
    expect(first.status).toBe('offline');
    expect(first.acked).toBe(200);
    expect(server.applied).toHaveLength(400);
    expect(await db.sync_outbox.where('status').equals('synced').count()).toBe(200);
    // lote 2 volta a pending com backoff; lote 3 nem saiu
    const backoff = (await db.sync_outbox.where('status').equals('pending').toArray()).filter((e) => e.next_retry_at);
    expect(backoff).toHaveLength(200);
    expect(await db.sync_outbox.where('status').equals('syncing').count()).toBe(0);

    controls.dropResponseOnPushCall = undefined; // conexão voltou
    const second = await syncNow({ ...deps(db, server, controls), now: later });
    expect(second.status).toBe('ok');
    expect(server.applied).toHaveLength(450);
    expect(new Set(server.applied).size).toBe(450);
    expect(server.table('client').size).toBe(450);
    expect(server.received.length).toBe(650); // 200 reenviados, nenhum aplicado duas vezes
    expect(await db.sync_outbox.where('status').equals('synced').count()).toBe(450);
  });

  it('erro de transporte aplica backoff exponencial 5 s → 10 min', () => {
    expect(outboxBackoffMs(1)).toBe(5_000);
    expect(outboxBackoffMs(2)).toBe(10_000);
    expect(outboxBackoffMs(3)).toBe(20_000);
    expect(outboxBackoffMs(30)).toBe(600_000);
  });
});

describe('cenário 4: fila com 500 operações', () => {
  it('push em lotes de 200 com a ordem de criação preservada', async () => {
    const db = freshDb();
    const server = new FakeSyncServer();
    const ids: string[] = [];
    for (let i = 0; i < 500; i += 1) {
      const ev = await enqueue(db, {
        entity_type: 'client',
        entity_id: `id-${i}`,
        operation: 'create',
        payload: { name: `C${i}`, status: 'active' },
        base_version: null,
      });
      ids.push(ev.id);
    }
    const res = await syncNow(deps(db, server));
    expect(res.status).toBe('ok');
    expect(server.pushCalls).toEqual([200, 200, 100]);
    expect(server.received.map((e) => e.id)).toEqual(ids);
  });
});

describe('cenário 5: app fechado no meio do envio', () => {
  it('eventos presos em syncing voltam a pending ao reabrir; dados continuam visíveis', async () => {
    const name = `fiscwise-test-stuck-${Math.random().toString(36).slice(2)}`;
    const db = new FiscWiseLocalDb('tenant-stuck', name);
    await createClient(db, clientData('Oficina Norte'));
    await createClient(db, clientData('Oficina Sul'));
    const all = await db.sync_outbox.toArray();
    await markSyncing(db, all.map((e) => e.id));
    db.close(); // aba fechada no meio do envio

    const reopened = new FiscWiseLocalDb('tenant-stuck', name);
    expect(await listPending(reopened)).toHaveLength(0);
    expect(await recoverStuckOutbox(reopened)).toBe(2);
    expect(await listPending(reopened)).toHaveLength(2);
    expect((await listClients(reopened)).map((c) => c.name)).toEqual(['Oficina Norte', 'Oficina Sul']);

    // e o próprio ciclo recupera (offline: nada sobe, nada fica em syncing)
    await markSyncing(reopened, all.map((e) => e.id));
    const run = await syncNow(deps(reopened, new FakeSyncServer(), { offline: true }));
    expect(run.status).toBe('offline');
    expect(await reopened.sync_outbox.where('status').equals('syncing').count()).toBe(0);
    expect(await reopened.sync_outbox.where('status').equals('pending').count()).toBe(2);
  });
});

describe('outbox: coalescência e regras', () => {
  it('updates do mesmo registro ainda pending viram um evento (payload mesclado, base_version do primeiro)', async () => {
    const db = freshDb();
    const server = new FakeSyncServer();
    const c = await createClient(db, clientData('Loja A'));
    await syncNow(deps(db, server));
    const base = (await db.clients.get(c.id))!.version;

    await updateClient(db, c.id, { name: 'Loja A1' });
    await updateClient(db, c.id, { email: 'a@a.com' });
    await updateClient(db, c.id, { name: 'Loja A2' });
    const pending = await listPending(db);
    expect(pending).toHaveLength(1);
    expect(pending[0].operation).toBe('update');
    // payload fica cifrado no IndexedDB; decifrado é o mesclado
    expect((await decryptEvent(db, pending[0])).payload).toEqual({ name: 'Loja A2', email: 'a@a.com' });
    expect(pending[0].base_version).toBe(base);

    // depois de uma desativação, novo update não é mesclado (ordem importa)
    await deactivateClient(db, c.id);
    await updateClient(db, c.id, { notes: 'x' });
    expect((await listPending(db)).map((e) => e.operation)).toEqual(['update', 'delete', 'update']);
  });

  it('rejeição do servidor fica em error com o motivo, sem retry; descartar remove', async () => {
    const db = freshDb();
    const server = new FakeSyncServer();
    const r = await createReceivable(db, { client_id: 'c', description: 'Honorário', amount: 100, due_date: '2026-12-10', status: 'pending' });
    await markReceivablePaid(db, r.id);
    await syncNow(deps(db, server));
    await db.receivables.update(r.id, { status: 'paid' });
    await enqueue(db, { entity_type: 'receivable', entity_id: r.id, operation: 'update', payload: { status: 'pending' }, base_version: 2 });
    await syncNow(deps(db, server));
    const errors = await db.sync_outbox.where('status').equals('error').toArray();
    expect(errors).toHaveLength(1);
    expect(errors[0].last_error).toContain('pago');
    expect((await db.receivables.get(r.id))?._sync_status).toBe('error');
    // não reenvia sozinho
    const calls = server.pushCalls.length;
    await syncNow({ ...deps(db, server), now: later });
    expect(server.pushCalls.length).toBe(calls);

    await discardEvent(db, errors[0].id);
    expect(await db.sync_outbox.where('status').equals('error').count()).toBe(0);
  });

  it('nota: rascunho offline + pedido de transmissão ficam Pendente de transmissão até o servidor', async () => {
    const db = freshDb();
    const server = new FakeSyncServer();
    const inv = await createInvoiceDraft(db, {
      issuer_id: 'iss-1',
      valor_servico: 100,
      descricao_servico: 'Consultoria',
      competencia: '2026-11-01',
    });
    await requestInvoiceEmission(db, inv.id);
    expect((await db.invoices.get(inv.id))?.status).toBe('pending_transmission');
    expect((await listPending(db)).map((e) => e.operation)).toEqual(['create', 'emit_requested']);

    await syncNow(deps(db, server));
    const local = await db.invoices.get(inv.id);
    expect(local?.status).toBe('queued');
    expect(local?.issued_at).toBeUndefined();
  });
});

describe('device_revoked', () => {
  it('apaga o banco local inteiro', async () => {
    const tenant = `revoked-${Math.random().toString(36).slice(2)}`;
    const db = openLocalDb(tenant);
    await createClient(db, clientData('Cliente revogado'));
    await setMeta(db, META.deviceToken, 'tok');
    expect(await Dexie.exists(db.name)).toBe(true);

    let revoked = false;
    const res = await syncNow(
      deps(db, new FakeSyncServer(), { offline: false, throwError: new DeviceRevokedError() }, {
        onRevoked: async () => {
          revoked = true;
          await wipeLocalDb(tenant);
        },
      }),
    );
    expect(res.status).toBe('revoked');
    expect(revoked).toBe(true);
    expect(await Dexie.exists(`fiscwise-${tenant}`)).toBe(false);
  });
});
