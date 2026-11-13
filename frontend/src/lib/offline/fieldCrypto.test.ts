import { describe, expect, it } from 'vitest';
import Dexie from 'dexie';
import { FiscWiseLocalDb, META, getMeta, openLocalDb, wipeLocalDb } from './db';
import { syncNow } from './engine';
import { createFakeTransport, FakeSyncServer } from './fakeSyncServer';
import {
  ENCRYPTED_PREFIX,
  decryptFields,
  encryptExistingRows,
  encryptFields,
  encryptValue,
  decryptValue,
  getLocalKey,
  isEncryptedValue,
} from './fieldCrypto';
import { createClient, getClient, listClients, updateClient } from './repositories';

let counter = 0;
function freshDb(): FiscWiseLocalDb {
  counter += 1;
  return new FiscWiseLocalDb(`tenant-c${counter}`, `fiscwise-crypto-${counter}-${Math.random().toString(36).slice(2)}`);
}

const sensitive = {
  name: 'Padaria Sol',
  entity_type: 'pj' as const,
  status: 'active' as const,
  document: '12.345.678/0001-90',
  email: 'contato@sol.com.br',
  phone: '11999990000',
  responsible_cpf: '123.456.789-09',
};

describe('criptografia dos campos sensíveis no IndexedDB', () => {
  it('grava documento, e-mail e telefone cifrados e devolve decifrado na leitura', async () => {
    const db = freshDb();
    const created = await createClient(db, sensitive);
    expect(created.email).toBe(sensitive.email);

    const raw = (await db.clients.get(created.id))!;
    for (const field of ['document', 'email', 'phone', 'responsible_cpf'] as const) {
      expect(raw[field]).toMatch(new RegExp(`^${ENCRYPTED_PREFIX}`));
      expect(JSON.stringify(raw)).not.toContain(sensitive[field]);
    }
    expect(raw.name).toBe('Padaria Sol'); // nome fica em claro (índice/ordenação)

    const rawEvent = (await db.sync_outbox.toArray())[0];
    expect(isEncryptedValue(rawEvent.payload.email)).toBe(true);

    expect((await getClient(db, created.id))?.document).toBe(sensitive.document);
    expect((await listClients(db))[0].phone).toBe(sensitive.phone);

    const updated = await updateClient(db, created.id, { email: 'novo@sol.com.br' });
    expect(updated.email).toBe('novo@sol.com.br');
    expect(isEncryptedValue((await db.clients.get(created.id))!.email)).toBe(true);
  });

  it('o servidor recebe o valor real e o pull volta a gravar cifrado', async () => {
    const db = freshDb();
    const server = new FakeSyncServer();
    const created = await createClient(db, sensitive);
    const transport = createFakeTransport(server, { offline: false });
    expect((await syncNow({ db, transport, reportStatus: false })).status).toBe('ok');
    expect(server.table('client').get(created.id)?.document).toBe(sensitive.document);

    server.seed('client', { id: globalThis.crypto.randomUUID(), name: 'Outro', email: 'outro@x.com', status: 'active' });
    await syncNow({ db, transport, reportStatus: false });
    const rows = await db.clients.toArray();
    expect(rows).toHaveLength(2);
    expect(rows.every((r) => isEncryptedValue(r.email))).toBe(true);
    expect((await listClients(db)).map((c) => c.email).sort()).toEqual(['contato@sol.com.br', 'outro@x.com']);
  });

  it('migra linhas antigas em texto puro e é idempotente', async () => {
    const db = freshDb();
    const id = globalThis.crypto.randomUUID();
    await db.clients.put({
      ...sensitive, id, tenant_id: db.tenantId, client_code: '', created_at: 'x', updated_at: 'x',
      version: 1, _sync_status: 'synced',
    } as never);
    expect((await listClients(db))[0].email).toBe(sensitive.email); // texto puro ainda legível
    expect(await encryptExistingRows(db)).toBe(1);
    expect(isEncryptedValue((await db.clients.get(id))!.document)).toBe(true);
    expect(await encryptExistingRows(db)).toBe(0);
    expect((await getClient(db, id))?.document).toBe(sensitive.document);
  });

  it('chave não exportável, presa ao campo, e apagada junto com o banco', async () => {
    const tenantId = `tenant-wipe-${Math.random().toString(36).slice(2)}`;
    const db = openLocalDb(tenantId);
    const key = await getLocalKey(db);
    expect(key.extractable).toBe(false);
    await expect(globalThis.crypto.subtle.exportKey('raw', key)).rejects.toThrow();
    expect(await getMeta(db, META.localKey)).toBeTruthy();

    const cipher = await encryptValue(key, 'email', 'a@a.com');
    expect(await decryptValue(key, 'email', cipher)).toBe('a@a.com');
    expect(await decryptValue(key, 'phone', cipher)).toBeNull(); // AAD: não troca de campo

    const stored = await encryptFields(db, 'client', { email: 'a@a.com', name: 'X' });
    await wipeLocalDb(tenantId);
    expect(await Dexie.exists(`fiscwise-${tenantId}`)).toBe(false);
    // banco novo = chave nova: o texto cifrado antigo não decifra mais
    const reopened = openLocalDb(tenantId);
    expect((await decryptFields(reopened, 'client', stored)).email).toBeNull();
    await wipeLocalDb(tenantId);
  });
});
