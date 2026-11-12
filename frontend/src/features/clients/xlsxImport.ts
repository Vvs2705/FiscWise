import type { AccountingClientCreate } from '@/lib/hooks/useOperations';

/** Colunas da aba "Dados do Cliente" de public/template-cadastro-cliente.xlsx. */
export const CLIENT_TEMPLATE_SHEET = 'Dados do Cliente';

const COLUMN_MAP: Record<string, keyof AccountingClientCreate> = {
  'Nome / Razao Social': 'name',
  'CPF / CNPJ': 'document',
  'Regime Tributario': 'tax_regime',
  'E-mail': 'email',
  'Telefone': 'phone',
  'Inscricao Municipal': 'municipal_registration',
  'Inscricao Estadual': 'state_registration',
  'Observacoes': 'notes',
};

// Linha de exemplo que vem no modelo — nunca vira cliente.
const EXAMPLE_ROW = { name: 'Empresa Exemplo Ltda', document: '12.345.678/0001-90' };

export interface ParsedClientRow {
  /** Número da linha na planilha (1 = cabeçalho). */
  rowNumber: number;
  name: string;
  payload?: AccountingClientCreate;
  error?: string;
}

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

function cell(value: unknown): string {
  if (value === null || value === undefined) return '';
  if (value instanceof Date) return value.toISOString().slice(0, 10);
  return String(value).trim();
}

/** Converte as linhas lidas do XLSX em payloads de POST /clients, validando cada linha. */
export function parseClientRows(rows: unknown[][]): ParsedClientRow[] {
  if (rows.length === 0) return [];
  const headers = rows[0].map((h) => cell(h));
  if (!headers.includes('Nome / Razao Social')) {
    return [{ rowNumber: 1, name: '', error: 'Cabeçalho do modelo não encontrado (coluna "Nome / Razao Social").' }];
  }

  const result: ParsedClientRow[] = [];
  rows.slice(1).forEach((row, index) => {
    const rowNumber = index + 2;
    const record: Record<string, string> = {};
    headers.forEach((header, i) => {
      record[header] = cell(row[i]);
    });
    if (Object.values(record).every((v) => v === '')) return; // linha vazia

    const payload: AccountingClientCreate = { name: '', entity_type: 'pj', status: 'active' };
    for (const [column, field] of Object.entries(COLUMN_MAP)) {
      const value = record[column];
      if (value) (payload as unknown as Record<string, string>)[field] = value;
    }

    if (payload.name === EXAMPLE_ROW.name && payload.document === EXAMPLE_ROW.document) return;

    const tipo = (record['Tipo (PJ ou PF)'] ?? '').toUpperCase();
    const digits = (payload.document ?? '').replace(/\D/g, '');
    payload.entity_type = tipo === 'PF' || (!tipo && digits.length === 11) ? 'pf' : 'pj';

    let error: string | undefined;
    if (!payload.name || payload.name.length < 2) error = 'Nome / Razão Social obrigatório.';
    else if (payload.document && digits.length !== 11 && digits.length !== 14) error = 'CPF/CNPJ com número de dígitos inválido.';
    else if (payload.email && !EMAIL_RE.test(payload.email)) error = 'E-mail inválido.';

    result.push(error ? { rowNumber, name: payload.name, error } : { rowNumber, name: payload.name, payload });
  });
  return result;
}

export interface ImportRowResult {
  rowNumber: number;
  name: string;
  ok: boolean;
  message: string;
}

/** Cria um a um, sem parar no primeiro erro; devolve o relatório por linha. */
export async function importClientRows(
  rows: ParsedClientRow[],
  create: (payload: AccountingClientCreate) => Promise<unknown>,
  describeError: (err: unknown) => string,
): Promise<ImportRowResult[]> {
  const results: ImportRowResult[] = [];
  for (const row of rows) {
    if (!row.payload) {
      results.push({ rowNumber: row.rowNumber, name: row.name, ok: false, message: row.error ?? 'Linha inválida.' });
      continue;
    }
    try {
      await create(row.payload);
      results.push({ rowNumber: row.rowNumber, name: row.name, ok: true, message: 'Cadastrado' });
    } catch (err) {
      results.push({ rowNumber: row.rowNumber, name: row.name, ok: false, message: describeError(err) });
    }
  }
  return results;
}
