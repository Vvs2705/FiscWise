/**
 * Utilitários de data em fuso LOCAL.
 *
 * `new Date('YYYY-MM-DD')` é interpretado como meia-noite UTC pelo JS; em
 * BRT (UTC-3) isso vira o dia anterior às 21h e faz prazos aparecerem com
 * -1 dia. Campos que o backend devolve como `date` (sem hora) devem passar
 * por `parseLocalDate`, que monta a data à meia-noite local.
 */

const DATE_ONLY = /^(\d{4})-(\d{2})-(\d{2})$/;

/** Converte 'YYYY-MM-DD' (ou ISO com hora) em Date local. Inválido → null. */
export function parseLocalDate(value: string | Date | null | undefined): Date | null {
  if (value == null || value === '') return null;
  if (value instanceof Date) return Number.isNaN(value.getTime()) ? null : new Date(value.getTime());
  const match = DATE_ONLY.exec(value);
  const parsed = match
    ? new Date(Number(match[1]), Number(match[2]) - 1, Number(match[3]))
    : new Date(value);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}

/** Meia-noite local do dia informado (ou de hoje). */
export function startOfLocalDay(value: Date = new Date()): Date {
  const d = new Date(value.getTime());
  d.setHours(0, 0, 0, 0);
  return d;
}

export function isSameLocalDay(a: string | Date | null | undefined, b: string | Date | null | undefined): boolean {
  const da = parseLocalDate(a);
  const db = parseLocalDate(b);
  if (!da || !db) return false;
  return da.getFullYear() === db.getFullYear() && da.getMonth() === db.getMonth() && da.getDate() === db.getDate();
}

/** Dias inteiros (calendário local) de `from` até `value`. Negativo = passado. */
export function daysUntilLocal(value: string | Date | null | undefined, from: Date = new Date()): number | null {
  const target = parseLocalDate(value);
  if (!target) return null;
  const a = startOfLocalDay(target);
  const b = startOfLocalDay(from);
  // Date.UTC neutraliza o horário de verão na diferença.
  const utcA = Date.UTC(a.getFullYear(), a.getMonth(), a.getDate());
  const utcB = Date.UTC(b.getFullYear(), b.getMonth(), b.getDate());
  return Math.round((utcA - utcB) / 86_400_000);
}

/** 'YYYY-MM-DD' no calendário local (ao contrário de toISOString, que é UTC). */
export function toLocalISODate(value: Date): string {
  const y = value.getFullYear();
  const m = String(value.getMonth() + 1).padStart(2, '0');
  const d = String(value.getDate()).padStart(2, '0');
  return `${y}-${m}-${d}`;
}

/** Soma dias no calendário local. */
export function addLocalDays(value: Date, days: number): Date {
  const d = new Date(value.getTime());
  d.setDate(d.getDate() + days);
  return d;
}

/** Formata em dd/mm/aaaa (pt-BR). Vazio/inválido → fallback. */
export function formatLocalDate(value: string | Date | null | undefined, fallback = '—'): string {
  const d = parseLocalDate(value);
  return d ? d.toLocaleDateString('pt-BR') : fallback;
}

/** 'Hoje', 'Amanhã' ou o nome do dia da semana em pt-BR ('Segunda', 'Terça'...). */
export function localDayLabel(value: string | Date, today: Date = new Date()): string {
  const diff = daysUntilLocal(value, today);
  if (diff === 0) return 'Hoje';
  if (diff === 1) return 'Amanhã';
  if (diff === -1) return 'Ontem';
  const d = parseLocalDate(value);
  if (!d) return '';
  const weekday = d.toLocaleDateString('pt-BR', { weekday: 'long' }).split('-')[0];
  return weekday.charAt(0).toUpperCase() + weekday.slice(1);
}

/** Competência 'YYYY-MM' de uma data (calendário local). */
export function toCompetence(value: Date): string {
  return `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, '0')}`;
}

/** Competência do mês anterior ao de `now`. */
export function previousCompetence(now: Date = new Date()): string {
  return toCompetence(new Date(now.getFullYear(), now.getMonth() - 1, 1));
}

/**
 * Competências do mês atual para trás: [atual, anterior, ...], `count` itens.
 * Ex.: count=13 → mês atual + últimas 12 competências.
 */
export function recentCompetences(count = 13, now: Date = new Date()): string[] {
  return Array.from({ length: count }, (_, i) => toCompetence(new Date(now.getFullYear(), now.getMonth() - i, 1)));
}

/** 'YYYY-MM' → 'Março/2026'. */
export function competenceLabel(competence: string): string {
  const match = /^(\d{4})-(\d{2})$/.exec(competence);
  if (!match) return competence;
  const d = new Date(Number(match[1]), Number(match[2]) - 1, 1);
  const month = d.toLocaleDateString('pt-BR', { month: 'long' });
  return `${month.charAt(0).toUpperCase()}${month.slice(1)}/${match[1]}`;
}
