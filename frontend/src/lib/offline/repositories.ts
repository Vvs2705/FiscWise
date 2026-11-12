/**
 * Repositórios local-first (OFFLINE_SYNC.md, seções 3.1, 5.2 e 6).
 * Toda escrita grava a linha da entidade E o evento da outbox na mesma
 * transação Dexie. A rede só sincroniza depois, pela engine.
 */
import type {
  AccountingClientCreate,
  CertificateCreate,
  DeadlineCreate,
  ReceivableCreate,
} from '@/lib/hooks/useOperations';
import type { InvoiceCreate, InvoiceResponse } from '@/features/invoices/services/invoices.service';
import type {
  AnyLocalRow,
  FiscWiseLocalDb,
  LocalCertificate,
  LocalClient,
  LocalDeadline,
  LocalInvoice,
  LocalReceivable,
  SyncEntityType,
  SyncOperation,
} from './db';
import { enqueue } from './outbox';

function nowIso(): string {
  return new Date().toISOString();
}

function newId(): string {
  return globalThis.crypto.randomUUID();
}

/** Remove chaves undefined (IndexedDB/JSON) */
function clean<T extends object>(obj: T): Record<string, unknown> {
  return Object.fromEntries(Object.entries(obj).filter(([, v]) => v !== undefined));
}

async function createLocal<R extends AnyLocalRow>(
  db: FiscWiseLocalDb,
  entity: SyncEntityType,
  payload: Record<string, unknown>,
  extra: Record<string, unknown> = {},
): Promise<R> {
  const table = db.entityTable(entity);
  const id = newId();
  const ts = nowIso();
  const row = {
    ...extra,
    ...payload,
    id,
    tenant_id: db.tenantId,
    created_at: ts,
    updated_at: ts,
    version: 1,
    _sync_status: 'pending',
    _local_updated_at: ts,
    _sync_error: null,
  } as unknown as R;
  await db.transaction('rw', table, db.sync_outbox, async () => {
    await table.add(row);
    await enqueue(db, { entity_type: entity, entity_id: id, operation: 'create', payload: { id, ...payload }, base_version: null });
  });
  return row;
}

async function updateLocal<R extends AnyLocalRow>(
  db: FiscWiseLocalDb,
  entity: SyncEntityType,
  id: string,
  patch: Record<string, unknown>,
  operation: SyncOperation = 'update',
  localOnly: Record<string, unknown> = {},
): Promise<R> {
  const table = db.entityTable(entity);
  return db.transaction('rw', table, db.sync_outbox, async () => {
    const current = await table.get(id);
    if (!current) throw new Error('Registro não encontrado no banco local.');
    const ts = nowIso();
    const next = {
      ...current,
      ...patch,
      ...localOnly,
      updated_at: ts,
      _sync_status: 'pending',
      _local_updated_at: ts,
      _sync_error: null,
    } as AnyLocalRow;
    await table.put(next);
    await enqueue(db, { entity_type: entity, entity_id: id, operation, payload: patch, base_version: current.version ?? 1 });
    return next as R;
  });
}

// ─── Clientes ────────────────────────────────────────────────────────────────

export async function listClients(db: FiscWiseLocalDb): Promise<LocalClient[]> {
  return db.clients.orderBy('name').toArray();
}

export async function getClient(db: FiscWiseLocalDb, id: string): Promise<LocalClient | undefined> {
  return db.clients.get(id);
}

export function createClient(db: FiscWiseLocalDb, data: AccountingClientCreate): Promise<LocalClient> {
  return createLocal<LocalClient & AnyLocalRow>(db, 'client', clean(data), { client_code: '' });
}

export function updateClient(db: FiscWiseLocalDb, id: string, patch: Partial<AccountingClientCreate>): Promise<LocalClient> {
  return updateLocal<LocalClient & AnyLocalRow>(db, 'client', id, clean(patch));
}

/** "Excluir" cliente = desativar (status inactive), operação `delete` (soft delete). */
export function deactivateClient(db: FiscWiseLocalDb, id: string): Promise<LocalClient> {
  return updateLocal<LocalClient & AnyLocalRow>(db, 'client', id, { status: 'inactive' }, 'delete');
}

// ─── Prazos / obrigações ─────────────────────────────────────────────────────

export async function listDeadlines(db: FiscWiseLocalDb, filter: { clientId?: string } = {}): Promise<LocalDeadline[]> {
  const rows = filter.clientId
    ? await db.deadlines.where('client_id').equals(filter.clientId).toArray()
    : await db.deadlines.toArray();
  return rows.sort((a, b) => a.due_date.localeCompare(b.due_date));
}

export function createDeadline(db: FiscWiseLocalDb, data: DeadlineCreate): Promise<LocalDeadline> {
  return createLocal<LocalDeadline & AnyLocalRow>(db, 'deadline', clean(data), { is_recurring: false });
}

export function updateDeadline(db: FiscWiseLocalDb, id: string, patch: Partial<DeadlineCreate>): Promise<LocalDeadline> {
  return updateLocal<LocalDeadline & AnyLocalRow>(db, 'deadline', id, clean(patch));
}

export function completeDeadline(db: FiscWiseLocalDb, id: string): Promise<LocalDeadline> {
  return updateLocal<LocalDeadline & AnyLocalRow>(db, 'deadline', id, { status: 'completed', completed_at: nowIso() });
}

export function cancelDeadline(db: FiscWiseLocalDb, id: string): Promise<LocalDeadline> {
  return updateLocal<LocalDeadline & AnyLocalRow>(db, 'deadline', id, { status: 'cancelled' }, 'delete');
}

// ─── Certificados (metadados) ────────────────────────────────────────────────

export async function listCertificates(db: FiscWiseLocalDb, filter: { clientId?: string } = {}): Promise<LocalCertificate[]> {
  const rows = filter.clientId
    ? await db.certificates.where('client_id').equals(filter.clientId).toArray()
    : await db.certificates.toArray();
  return rows.sort((a, b) => a.valid_until.localeCompare(b.valid_until));
}

export function createCertificate(db: FiscWiseLocalDb, data: CertificateCreate): Promise<LocalCertificate> {
  return createLocal<LocalCertificate & AnyLocalRow>(db, 'certificate', clean(data));
}

export function updateCertificate(db: FiscWiseLocalDb, id: string, patch: Partial<CertificateCreate>): Promise<LocalCertificate> {
  return updateLocal<LocalCertificate & AnyLocalRow>(db, 'certificate', id, clean(patch));
}

/** Bloquear certificado = status revoked (soft delete). */
export function revokeCertificate(db: FiscWiseLocalDb, id: string): Promise<LocalCertificate> {
  return updateLocal<LocalCertificate & AnyLocalRow>(db, 'certificate', id, { status: 'revoked' }, 'delete');
}

// ─── Honorários (contas a receber) ───────────────────────────────────────────

export async function listReceivables(db: FiscWiseLocalDb, filter: { clientId?: string } = {}): Promise<LocalReceivable[]> {
  const rows = filter.clientId
    ? await db.receivables.where('client_id').equals(filter.clientId).toArray()
    : await db.receivables.toArray();
  return rows.sort((a, b) => a.due_date.localeCompare(b.due_date));
}

export function createReceivable(db: FiscWiseLocalDb, data: ReceivableCreate): Promise<LocalReceivable> {
  return createLocal<LocalReceivable & AnyLocalRow>(db, 'receivable', clean(data));
}

export function updateReceivable(db: FiscWiseLocalDb, id: string, patch: Partial<ReceivableCreate>): Promise<LocalReceivable> {
  return updateLocal<LocalReceivable & AnyLocalRow>(db, 'receivable', id, clean(patch));
}

export function markReceivablePaid(db: FiscWiseLocalDb, id: string, paidAt: string = nowIso()): Promise<LocalReceivable> {
  return updateLocal<LocalReceivable & AnyLocalRow>(db, 'receivable', id, { status: 'paid', paid_at: paidAt });
}

export function cancelReceivable(db: FiscWiseLocalDb, id: string): Promise<LocalReceivable> {
  return updateLocal<LocalReceivable & AnyLocalRow>(db, 'receivable', id, { status: 'cancelled' }, 'delete');
}

// ─── Notas fiscais (só rascunho e pedido de transmissão — seção 6) ───────────

export async function listInvoices(db: FiscWiseLocalDb): Promise<LocalInvoice[]> {
  const rows = await db.invoices.toArray();
  return rows.sort((a, b) => b.created_at.localeCompare(a.created_at));
}

export async function getInvoice(db: FiscWiseLocalDb, id: string): Promise<LocalInvoice | undefined> {
  return db.invoices.get(id);
}

export function createInvoiceDraft(db: FiscWiseLocalDb, data: InvoiceCreate): Promise<LocalInvoice> {
  return createLocal<LocalInvoice & AnyLocalRow>(db, 'invoice', { ...clean(data), status: 'draft' });
}

/** Status de nota que permitem pedir transmissão. */
const EMITTABLE_STATUSES = new Set(['draft', 'rejected']);

/**
 * Pede a transmissão da nota. Offline o FiscWise NÃO emite: grava o status local
 * `pending_transmission` e enfileira `emit_requested`; quem autoriza é o
 * servidor/SEFAZ/prefeitura quando a conexão voltar.
 *
 * `serverRow`: nota vinda da API (React Query), usada se ela ainda não estiver no
 * banco local (o pull ainda não rodou).
 */
export async function requestInvoiceEmission(
  db: FiscWiseLocalDb,
  id: string,
  serverRow?: InvoiceResponse & { version?: number },
): Promise<LocalInvoice> {
  return db.transaction('rw', db.invoices, db.sync_outbox, async () => {
    let current = await db.invoices.get(id);
    if (!current && serverRow) {
      current = { ...serverRow, version: serverRow.version ?? 1, _sync_status: 'synced', _sync_error: null };
      await db.invoices.put(current);
    }
    if (!current) throw new Error('Nota não encontrada no banco local.');
    if (current.status === 'pending_transmission') return current;
    if (!EMITTABLE_STATUSES.has(current.status)) {
      throw new Error('Só rascunhos ou notas rejeitadas podem ser enviados para transmissão.');
    }
    const ts = nowIso();
    const next: LocalInvoice = {
      ...current,
      status: 'pending_transmission',
      updated_at: ts,
      _sync_status: 'pending',
      _local_updated_at: ts,
      _sync_error: null,
    };
    await db.invoices.put(next);
    await enqueue(db, {
      entity_type: 'invoice',
      entity_id: id,
      operation: 'emit_requested',
      payload: {},
      base_version: current.version ?? 1,
    });
    return next;
  });
}
