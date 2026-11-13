import type { AccountingClientCreate } from '@/lib/hooks/useOperations';

/** Colunas da aba "Dados do Cliente" de public/template-cadastro-cliente.xlsx. */
export const CLIENT_TEMPLATE_SHEET = 'Dados do Cliente';

type ClientField = keyof AccountingClientCreate | 'tipo';

/**
 * Nomes de coluna aceitos para cada campo, já normalizados (sem acento, minúsculo,
 * pontuação vira espaço). O primeiro é o do nosso modelo; os outros cobrem as
 * exportações mais comuns de outros sistemas contábeis e planilhas próprias.
 */
const COLUMN_ALIASES: Array<[ClientField, string[]]> = [
  ['name', ['nome razao social', 'razao social', 'nome empresarial', 'nome do cliente', 'cliente', 'empresa', 'nome']],
  ['document', ['cpf cnpj', 'cnpj cpf', 'cnpj', 'cpf', 'documento', 'cnpj ou cpf', 'cpf ou cnpj']],
  ['tipo', ['tipo pj ou pf', 'tipo de pessoa', 'tipo pessoa', 'pessoa', 'tipo']],
  ['tax_regime', ['regime tributario', 'regime de tributacao', 'regime', 'tributacao']],
  ['email', ['e mail', 'email', 'e mail principal', 'email de contato']],
  ['phone', ['telefone', 'fone', 'celular', 'whatsapp', 'telefone principal']],
  ['municipal_registration', ['inscricao municipal', 'insc municipal', 'im']],
  ['state_registration', ['inscricao estadual', 'insc estadual', 'ie']],
  ['notes', ['observacoes', 'observacao', 'obs', 'anotacoes']],
];

const REGIMES: Array<[RegExp, string]> = [
  [/^mei|microempreendedor/, 'MEI'],
  [/simples/, 'Simples Nacional'],
  [/presumido/, 'Lucro Presumido'],
  [/real/, 'Lucro Real'],
];

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

export function normalizeHeader(header: string): string {
  return header
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, ' ')
    .trim();
}

/** Para cada campo, o índice da coluna que o preenche (ou ausente). */
export function mapColumns(headers: string[]): Partial<Record<ClientField, number>> {
  const normalized = headers.map((h) => normalizeHeader(h));
  const used = new Set<number>();
  const map: Partial<Record<ClientField, number>> = {};
  for (const [field, aliases] of COLUMN_ALIASES) {
    for (const alias of aliases) {
      const index = normalized.findIndex((h, i) => h === alias && !used.has(i));
      if (index >= 0) {
        map[field] = index;
        used.add(index);
        break;
      }
    }
  }
  return map;
}

/** "simples", "SIMPLES NACIONAL", "Lucro presumido"… viram o valor do cadastro. */
export function normalizeRegime(value: string): string {
  const v = normalizeHeader(value);
  for (const [re, label] of REGIMES) if (re.test(v)) return label;
  return value;
}

/** Converte as linhas lidas da planilha (XLSX ou CSV) em payloads de POST /clients, validando cada linha. */
export function parseClientRows(rows: unknown[][]): ParsedClientRow[] {
  if (rows.length === 0) return [];
  const columns = mapColumns(rows[0].map((h) => cell(h)));
  if (columns.name === undefined) {
    return [{
      rowNumber: 1,
      name: '',
      error: 'Cabeçalho não reconhecido: a planilha precisa de uma coluna "Nome / Razao Social" (ou "Razão Social", "Nome").',
    }];
  }

  const result: ParsedClientRow[] = [];
  rows.slice(1).forEach((row, index) => {
    const rowNumber = index + 2;
    if (row.every((v) => cell(v) === '')) return; // linha vazia
    const get = (field: ClientField) => {
      const i = columns[field];
      return i === undefined ? '' : cell(row[i]);
    };

    const payload: AccountingClientCreate = { name: '', entity_type: 'pj', status: 'active' };
    for (const [field] of COLUMN_ALIASES) {
      if (field === 'tipo') continue;
      const value = get(field);
      if (value) (payload as unknown as Record<string, string>)[field] = value;
    }
    if (payload.tax_regime) payload.tax_regime = normalizeRegime(payload.tax_regime);

    if (payload.name === EXAMPLE_ROW.name && payload.document === EXAMPLE_ROW.document) return;

    const tipo = get('tipo').toUpperCase();
    const digits = (payload.document ?? '').replace(/\D/g, '');
    const isPf = tipo === 'PF' || tipo.startsWith('FISICA') || tipo.startsWith('FÍSICA');
    payload.entity_type = isPf || (!tipo && digits.length === 11) ? 'pf' : 'pj';

    let error: string | undefined;
    if (!payload.name || payload.name.length < 2) error = 'Nome / Razão Social obrigatório.';
    else if (payload.document && digits.length !== 11 && digits.length !== 14) error = 'CPF/CNPJ com número de dígitos inválido.';
    else if (payload.email && !EMAIL_RE.test(payload.email)) error = 'E-mail inválido.';

    result.push(error ? { rowNumber, name: payload.name, error } : { rowNumber, name: payload.name, payload });
  });
  return result;
}

/**
 * Lê um CSV exportado de outro sistema ou do Excel. Detecta o separador
 * (";" do Excel em português, "," ou tabulação), aceita aspas e quebras de
 * linha dentro de aspas, e ignora o BOM.
 */
export function parseCsv(text: string): string[][] {
  const src = text.replace(/^\uFEFF/, '');
  const firstLine = src.split(/\r?\n/, 1)[0] ?? '';
  const count = (ch: string) => firstLine.split(ch).length - 1;
  const delimiter = [';', ',', '\t'].reduce((best, ch) => (count(ch) > count(best) ? ch : best), ';');

  const rows: string[][] = [];
  let row: string[] = [];
  let field = '';
  let quoted = false;
  for (let i = 0; i < src.length; i++) {
    const ch = src[i];
    if (quoted) {
      if (ch === '"') {
        if (src[i + 1] === '"') {
          field += '"';
          i++;
        } else quoted = false;
      } else field += ch;
    } else if (ch === '"') quoted = true;
    else if (ch === delimiter) {
      row.push(field);
      field = '';
    } else if (ch === '\n' || ch === '\r') {
      if (ch === '\r' && src[i + 1] === '\n') i++;
      row.push(field);
      rows.push(row);
      row = [];
      field = '';
    } else field += ch;
  }
  if (field !== '' || row.length > 0) {
    row.push(field);
    rows.push(row);
  }
  return rows;
}

/** Texto do arquivo: UTF-8 e, se não for, Windows-1252 (CSV salvo pelo Excel). */
async function readText(file: Blob): Promise<string> {
  const buffer = await file.arrayBuffer();
  try {
    return new TextDecoder('utf-8', { fatal: true }).decode(buffer);
  } catch {
    return new TextDecoder('windows-1252').decode(buffer);
  }
}

export const SPREADSHEET_ACCEPT = '.xlsx,.csv';

export function isSpreadsheetFile(name: string): boolean {
  const ext = name.split('.').pop()?.toLowerCase();
  return ext === 'xlsx' || ext === 'csv';
}

/** Linhas de um .xlsx (aba do modelo, ou a primeira) ou de um .csv. */
export async function readSpreadsheetRows(file: File): Promise<unknown[][]> {
  if (file.name.toLowerCase().endsWith('.csv')) return parseCsv(await readText(file));
  // /universal: lê o Blob no próprio thread, sem Web Worker (o /browser usa worker).
  const { default: readExcelFile } = await import('read-excel-file/universal');
  const sheets = await readExcelFile(file);
  const sheet = sheets.find((s) => s.sheet === CLIENT_TEMPLATE_SHEET) ?? sheets[0];
  return (sheet?.data ?? []) as unknown[][];
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
