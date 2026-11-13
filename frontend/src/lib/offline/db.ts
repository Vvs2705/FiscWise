/**
 * Banco local (IndexedDB via Dexie) do modo offline-first.
 * Um banco por escritório: `fiscwise-<tenant_id>` (OFFLINE_SYNC.md, seção 4.3).
 */
import Dexie, { type Table } from 'dexie';
import type {
  AccountingClient,
  AccountReceivable,
  DeadlineItem,
  DigitalCertificate,
} from '@/lib/hooks/useOperations';
import type { InvoiceResponse } from '@/features/invoices/services/invoices.service';

export type SyncEntityType = 'client' | 'deadline' | 'certificate' | 'receivable' | 'invoice';
export type EntityStoreName = 'clients' | 'deadlines' | 'certificates' | 'receivables' | 'invoices';
export type SyncOperation = 'create' | 'update' | 'delete' | 'emit_requested';
export type OutboxStatus = 'pending' | 'syncing' | 'synced' | 'error';
export type LocalSyncStatus = 'synced' | 'pending' | 'error';

/** Ordem fixa de pull (e da carga inicial "Baixando dados do escritório (x/5)"). */
export const SYNC_ENTITIES: readonly SyncEntityType[] = ['client', 'deadline', 'certificate', 'receivable', 'invoice'];

export const ENTITY_STORE: Record<SyncEntityType, EntityStoreName> = {
  client: 'clients',
  deadline: 'deadlines',
  certificate: 'certificates',
  receivable: 'receivables',
  invoice: 'invoices',
};

export const ENTITY_LABEL: Record<SyncEntityType, string> = {
  client: 'Clientes',
  deadline: 'Prazos e obrigações',
  certificate: 'Certificados',
  receivable: 'Honorários',
  invoice: 'Notas fiscais',
};

/** Colunas só locais (nunca sobem para o servidor). */
export interface LocalRowMeta {
  version: number;
  _sync_status: LocalSyncStatus;
  _local_updated_at?: string | null;
  _sync_error?: string | null;
}

export type LocalClient = AccountingClient & LocalRowMeta;
export type LocalDeadline = DeadlineItem & LocalRowMeta;
export type LocalCertificate = DigitalCertificate & LocalRowMeta;
export type LocalReceivable = AccountReceivable & LocalRowMeta;
/** `pending_transmission` existe só no banco local (no servidor vira `queued`). */
export type LocalInvoice = InvoiceResponse & LocalRowMeta;

export type AnyLocalRow = { id: string } & LocalRowMeta & Record<string, unknown>;

export interface OutboxEvent {
  id: string;
  /** Ordem de criação estável (created_at pode empatar no mesmo milissegundo). */
  seq: number;
  entity_type: SyncEntityType;
  entity_id: string;
  operation: SyncOperation;
  payload: Record<string, unknown>;
  base_version: number | null;
  created_at: string;
  attempts: number;
  status: OutboxStatus;
  last_error: string | null;
  next_retry_at: string | null;
  synced_at?: string | null;
}

export interface SyncMetaRow {
  key: string;
  value: unknown;
}

export interface LocalConflict {
  /** id do evento que causou a sobrescrita */
  id: string;
  entity_type: SyncEntityType;
  entity_id: string;
  fields_overwritten: Record<string, { server: unknown; client: unknown }>;
  created_at: string;
  resolved_at: string | null;
  /** 0 = aberto, 1 = resolvido (IndexedDB não indexa null/boolean) */
  resolved: 0 | 1;
}

export class FiscWiseLocalDb extends Dexie {
  clients!: Table<LocalClient, string>;
  deadlines!: Table<LocalDeadline, string>;
  certificates!: Table<LocalCertificate, string>;
  receivables!: Table<LocalReceivable, string>;
  invoices!: Table<LocalInvoice, string>;
  sync_outbox!: Table<OutboxEvent, string>;
  sync_meta!: Table<SyncMetaRow, string>;
  sync_conflicts!: Table<LocalConflict, string>;

  readonly tenantId: string;

  constructor(tenantId: string, name: string = localDbName(tenantId)) {
    super(name);
    this.tenantId = tenantId;
    this.version(1).stores({
      clients: 'id, status, updated_at, name',
      deadlines: 'id, client_id, status, due_date, updated_at',
      certificates: 'id, client_id, status, valid_until, updated_at',
      receivables: 'id, client_id, status, due_date, updated_at',
      invoices: 'id, client_id, status, updated_at',
      sync_outbox: 'id, &seq, status, [entity_type+entity_id], created_at',
      sync_meta: 'key',
      sync_conflicts: 'id, resolved, entity_type, entity_id, created_at',
    });
  }

  /** Tabela genérica da entidade (para a engine). */
  entityTable(entity: SyncEntityType): Table<AnyLocalRow, string> {
    return this.table(ENTITY_STORE[entity]) as unknown as Table<AnyLocalRow, string>;
  }
}

export function localDbName(tenantId: string): string {
  return `fiscwise-${tenantId}`;
}

const openDbs = new Map<string, FiscWiseLocalDb>();

export function openLocalDb(tenantId: string): FiscWiseLocalDb {
  if (!tenantId) throw new Error('tenant_id obrigatório para abrir o banco local');
  let db = openDbs.get(tenantId);
  if (!db) {
    db = new FiscWiseLocalDb(tenantId);
    openDbs.set(tenantId, db);
  }
  return db;
}

/** Apaga o banco local inteiro do escritório (logout explícito, dispositivo revogado). */
export async function wipeLocalDb(tenantId: string): Promise<void> {
  const db = openDbs.get(tenantId);
  openDbs.delete(tenantId);
  if (db) db.close();
  await Dexie.delete(localDbName(tenantId));
}

/** Cache do service worker com respostas da API (seção 7.1); apagado junto com o banco. */
export { API_CACHE_NAME, clearApiCache } from './apiCache';

// ─── sync_meta ───────────────────────────────────────────────────────────────

export async function getMeta<T>(db: FiscWiseLocalDb, key: string): Promise<T | undefined> {
  const row = await db.sync_meta.get(key);
  return row?.value as T | undefined;
}

export async function setMeta(db: FiscWiseLocalDb, key: string, value: unknown): Promise<void> {
  await db.sync_meta.put({ key, value });
}

export async function deleteMeta(db: FiscWiseLocalDb, key: string): Promise<void> {
  await db.sync_meta.delete(key);
}

export const META = {
  deviceId: 'device_id',
  deviceToken: 'device_token',
  lastSyncAt: 'last_sync_at',
  lastError: 'last_error',
  storagePersistRequested: 'storage_persist_requested',
  /** CryptoKey AES-GCM não exportável dos campos sensíveis (fieldCrypto.ts) */
  localKey: 'local_key',
  cursor: (entity: SyncEntityType) => `cursor:${entity}`,
} as const;
