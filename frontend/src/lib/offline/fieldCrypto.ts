/**
 * Criptografia dos campos sensíveis no banco local (OFFLINE_SYNC.md, seção 9).
 *
 * CPF/CNPJ, e-mail e telefone dos clientes do escritório (e do tomador da nota)
 * são gravados no IndexedDB cifrados com AES-GCM 256 (WebCrypto). A chave é
 * gerada no navegador como **não exportável** e fica no próprio banco do
 * escritório (`sync_meta`): nenhum script consegue ler os bytes da chave, só
 * pedir ao navegador para cifrar/decifrar. Apagar o banco (logout explícito,
 * dispositivo revogado) apaga a chave junto, e o que sobrar em disco fica ilegível.
 *
 * O que protege: cópia dos arquivos do perfil do navegador, backup, extensão ou
 * ferramenta que leia o IndexedDB em repouso. O que não protege: um script
 * rodando na própria origem (XSS) enquanto a sessão está aberta, que pode pedir
 * a decifragem como o app faz; para isso vale a CSP.
 *
 * Os valores cifrados nunca entram em índice do Dexie (só `name`, datas e
 * status são indexados), então a busca local continua funcionando: o app
 * decifra na leitura e filtra em memória.
 *
 * Formato do valor gravado: `enc1:<base64(iv de 12 bytes || texto cifrado)>`,
 * com o nome do campo como dado associado (AAD), para um valor não poder ser
 * trocado de campo. Valor sem o prefixo é lido como texto puro (linhas antigas,
 * migradas por `encryptExistingRows`).
 */
import { META, getMeta, type FiscWiseLocalDb, type LocalConflict, type OutboxEvent, type SyncEntityType } from './db';

export const ENCRYPTED_PREFIX = 'enc1:';

/** Campos cifrados por entidade. */
export const SENSITIVE_FIELDS: Record<SyncEntityType, readonly string[]> = {
  client: ['document', 'email', 'phone', 'responsible_cpf', 'responsible_email', 'responsible_phone'],
  invoice: ['tomador_cpf_cnpj', 'tomador_email'],
  deadline: [],
  certificate: [],
  receivable: [],
};

const ALGORITHM = 'AES-GCM';
const IV_BYTES = 12;
const encoder = new TextEncoder();
const decoder = new TextDecoder();

const keys = new WeakMap<FiscWiseLocalDb, Promise<CryptoKey>>();

function subtle(): SubtleCrypto {
  const s = globalThis.crypto?.subtle;
  if (!s) throw new Error('WebCrypto indisponível: o modo offline exige HTTPS.');
  return s;
}

async function loadOrCreateKey(db: FiscWiseLocalDb): Promise<CryptoKey> {
  const existing = await getMeta<CryptoKey>(db, META.localKey);
  if (existing) return existing;
  const generated = await subtle().generateKey({ name: ALGORITHM, length: 256 }, false, ['encrypt', 'decrypt']);
  // Outra aba pode ter criado a chave enquanto esta gerava: quem gravou primeiro vence.
  return db.transaction('rw', db.sync_meta, async () => {
    const again = await db.sync_meta.get(META.localKey);
    if (again?.value) return again.value as CryptoKey;
    await db.sync_meta.put({ key: META.localKey, value: generated });
    return generated;
  });
}

/** Chave do banco local do escritório (criada na primeira vez). */
export function getLocalKey(db: FiscWiseLocalDb): Promise<CryptoKey> {
  let key = keys.get(db);
  if (!key) {
    key = loadOrCreateKey(db);
    key.catch(() => keys.delete(db));
    keys.set(db, key);
  }
  return key;
}

export function isEncryptedValue(value: unknown): value is string {
  return typeof value === 'string' && value.startsWith(ENCRYPTED_PREFIX);
}

function toBase64(bytes: Uint8Array): string {
  let bin = '';
  for (let i = 0; i < bytes.length; i += 1) bin += String.fromCharCode(bytes[i]);
  return btoa(bin);
}

function fromBase64(text: string): Uint8Array {
  const bin = atob(text);
  const out = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i += 1) out[i] = bin.charCodeAt(i);
  return out;
}

export async function encryptValue(key: CryptoKey, field: string, value: string): Promise<string> {
  const iv = globalThis.crypto.getRandomValues(new Uint8Array(IV_BYTES));
  const cipher = await subtle().encrypt(
    { name: ALGORITHM, iv, additionalData: encoder.encode(field) },
    key,
    encoder.encode(value),
  );
  const packed = new Uint8Array(IV_BYTES + cipher.byteLength);
  packed.set(iv, 0);
  packed.set(new Uint8Array(cipher), IV_BYTES);
  return ENCRYPTED_PREFIX + toBase64(packed);
}

/** Decifra; valor que não decifra (chave trocada, dado corrompido) vira null. */
export async function decryptValue(key: CryptoKey, field: string, value: string): Promise<string | null> {
  try {
    const packed = fromBase64(value.slice(ENCRYPTED_PREFIX.length));
    const plain = await subtle().decrypt(
      { name: ALGORITHM, iv: packed.slice(0, IV_BYTES), additionalData: encoder.encode(field) },
      key,
      packed.slice(IV_BYTES),
    );
    return decoder.decode(plain);
  } catch {
    return null;
  }
}

function needsWork(entity: SyncEntityType, obj: Record<string, unknown> | null | undefined): boolean {
  return !!obj && SENSITIVE_FIELDS[entity].some((f) => f in obj);
}

/**
 * Cifra os campos sensíveis de uma linha ou payload (cópia nova; o original
 * não muda). Chamar ANTES de abrir a transação Dexie: WebCrypto é assíncrono
 * fora do IndexedDB e fecharia a transação.
 */
export async function encryptFields<T extends object>(db: FiscWiseLocalDb, entity: SyncEntityType, obj: T): Promise<T> {
  const record = obj as Record<string, unknown>;
  if (!needsWork(entity, record)) return obj;
  const key = await getLocalKey(db);
  const out: Record<string, unknown> = { ...record };
  for (const field of SENSITIVE_FIELDS[entity]) {
    const value = out[field];
    if (typeof value === 'string' && value !== '' && !isEncryptedValue(value)) {
      out[field] = await encryptValue(key, field, value);
    }
  }
  return out as T;
}

/** Decifra os campos sensíveis (cópia nova). Texto puro antigo passa direto. */
export async function decryptFields<T extends object>(db: FiscWiseLocalDb, entity: SyncEntityType, obj: T): Promise<T> {
  const record = obj as Record<string, unknown>;
  if (!needsWork(entity, record)) return obj;
  const fields = SENSITIVE_FIELDS[entity].filter((f) => isEncryptedValue(record[f]));
  if (fields.length === 0) return obj;
  const key = await getLocalKey(db);
  const out: Record<string, unknown> = { ...record };
  for (const field of fields) out[field] = await decryptValue(key, field, record[field] as string);
  return out as T;
}

export function encryptRows<T extends object>(db: FiscWiseLocalDb, entity: SyncEntityType, rows: T[]): Promise<T[]> {
  if (SENSITIVE_FIELDS[entity].length === 0) return Promise.resolve(rows);
  return Promise.all(rows.map((row) => encryptFields(db, entity, row)));
}

export function decryptRows<T extends object>(db: FiscWiseLocalDb, entity: SyncEntityType, rows: T[]): Promise<T[]> {
  if (SENSITIVE_FIELDS[entity].length === 0) return Promise.resolve(rows);
  return Promise.all(rows.map((row) => decryptFields(db, entity, row)));
}

type OverwrittenFields = LocalConflict['fields_overwritten'];

async function mapConflictValues(
  db: FiscWiseLocalDb,
  entity: SyncEntityType,
  fields: OverwrittenFields,
  fn: (key: CryptoKey, field: string, value: string) => Promise<string | null>,
  applies: (value: unknown) => boolean,
): Promise<OverwrittenFields> {
  const sensitive = SENSITIVE_FIELDS[entity].filter((f) => f in fields);
  if (sensitive.length === 0) return fields;
  const key = await getLocalKey(db);
  const out: OverwrittenFields = { ...fields };
  for (const field of sensitive) {
    const pair = { ...fields[field] };
    if (applies(pair.server)) pair.server = await fn(key, field, pair.server as string);
    if (applies(pair.client)) pair.client = await fn(key, field, pair.client as string);
    out[field] = pair;
  }
  return out;
}

/** Cifra os valores "antes/depois" de um conflito vindo do servidor. */
export function encryptConflictFields(db: FiscWiseLocalDb, entity: SyncEntityType, fields: OverwrittenFields) {
  return mapConflictValues(db, entity, fields, encryptValue, (v) => typeof v === 'string' && v !== '' && !isEncryptedValue(v));
}

export async function decryptConflict(db: FiscWiseLocalDb, conflict: LocalConflict): Promise<LocalConflict> {
  const fields = await mapConflictValues(db, conflict.entity_type, conflict.fields_overwritten, decryptValue, isEncryptedValue);
  return fields === conflict.fields_overwritten ? conflict : { ...conflict, fields_overwritten: fields };
}

export async function decryptEvent(db: FiscWiseLocalDb, event: OutboxEvent): Promise<OutboxEvent> {
  const payload = await decryptFields(db, event.entity_type, event.payload);
  return payload === event.payload ? event : { ...event, payload };
}

/**
 * Cifra o que ainda estiver em texto puro (bancos criados antes desta versão).
 * Idempotente; roda na abertura da sessão offline.
 */
export async function encryptExistingRows(db: FiscWiseLocalDb): Promise<number> {
  let changed = 0;
  for (const entity of Object.keys(SENSITIVE_FIELDS) as SyncEntityType[]) {
    const fields = SENSITIVE_FIELDS[entity];
    if (fields.length === 0) continue;
    const table = db.entityTable(entity);
    const plain = (await table.toArray()).filter((row) =>
      fields.some((f) => typeof row[f] === 'string' && row[f] !== '' && !isEncryptedValue(row[f])),
    );
    if (plain.length === 0) continue;
    const encrypted = await encryptRows(db, entity, plain);
    // Só grava se a linha não mudou entre a leitura e agora (sync em paralelo).
    await db.transaction('rw', table, async () => {
      for (let i = 0; i < encrypted.length; i += 1) {
        const current = await table.get(plain[i].id);
        if (current && current.updated_at === plain[i].updated_at && current.version === plain[i].version) {
          await table.put(encrypted[i]);
          changed += 1;
        }
      }
    });
  }
  const events = (await db.sync_outbox.toArray()).filter((e) =>
    SENSITIVE_FIELDS[e.entity_type].some((f) => typeof e.payload[f] === 'string' && e.payload[f] !== '' && !isEncryptedValue(e.payload[f])),
  );
  if (events.length > 0) {
    const payloads = await Promise.all(events.map((e) => encryptFields(db, e.entity_type, e.payload)));
    await db.transaction('rw', db.sync_outbox, async () => {
      for (let i = 0; i < events.length; i += 1) {
        const current = await db.sync_outbox.get(events[i].id);
        if (current && JSON.stringify(current.payload) === JSON.stringify(events[i].payload)) {
          await db.sync_outbox.put({ ...current, payload: payloads[i] });
          changed += 1;
        }
      }
    });
  }
  return changed;
}
