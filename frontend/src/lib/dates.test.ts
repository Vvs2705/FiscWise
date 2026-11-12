import { describe, expect, it } from 'vitest';
import {
  addLocalDays,
  competenceLabel,
  daysUntilLocal,
  formatLocalDate,
  isSameLocalDay,
  localDayLabel,
  parseLocalDate,
  previousCompetence,
  recentCompetences,
  toLocalISODate,
} from './dates';

describe('parseLocalDate', () => {
  it('interpreta YYYY-MM-DD como meia-noite local (não UTC)', () => {
    const d = parseLocalDate('2026-03-15')!;
    expect(d.getFullYear()).toBe(2026);
    expect(d.getMonth()).toBe(2);
    expect(d.getDate()).toBe(15);
    expect(d.getHours()).toBe(0);
  });

  it('aceita ISO com hora e rejeita inválidos', () => {
    expect(parseLocalDate('2026-03-15T10:30:00')?.getHours()).toBe(10);
    expect(parseLocalDate('')).toBeNull();
    expect(parseLocalDate(null)).toBeNull();
    expect(parseLocalDate('abc')).toBeNull();
  });
});

describe('comparações de dia', () => {
  it('isSameLocalDay compara calendário local', () => {
    expect(isSameLocalDay('2026-03-15', new Date(2026, 2, 15, 23, 59))).toBe(true);
    expect(isSameLocalDay('2026-03-15', new Date(2026, 2, 14, 23, 59))).toBe(false);
  });

  it('daysUntilLocal conta dias de calendário', () => {
    const now = new Date(2026, 2, 15, 22, 0);
    expect(daysUntilLocal('2026-03-15', now)).toBe(0);
    expect(daysUntilLocal('2026-03-16', now)).toBe(1);
    expect(daysUntilLocal('2026-03-10', now)).toBe(-5);
    expect(daysUntilLocal(undefined, now)).toBeNull();
  });

  it('toLocalISODate usa o dia local', () => {
    expect(toLocalISODate(new Date(2026, 0, 5, 23, 30))).toBe('2026-01-05');
    expect(toLocalISODate(addLocalDays(new Date(2026, 0, 31), 1))).toBe('2026-02-01');
  });

  it('formatLocalDate formata pt-BR e usa fallback', () => {
    expect(formatLocalDate('2026-03-15')).toBe('15/03/2026');
    expect(formatLocalDate(null)).toBe('—');
  });
});

describe('localDayLabel', () => {
  // 12/11/2026 é uma quinta-feira
  const today = new Date(2026, 10, 12, 9, 0);
  it('Hoje / Amanhã / dia da semana real', () => {
    expect(localDayLabel('2026-11-12', today)).toBe('Hoje');
    expect(localDayLabel('2026-11-13', today)).toBe('Amanhã');
    expect(localDayLabel('2026-11-14', today)).toBe('Sábado');
    expect(localDayLabel('2026-11-16', today)).toBe('Segunda');
    expect(localDayLabel('2026-11-17', today)).toBe('Terça');
  });
});

describe('competências', () => {
  const now = new Date(2026, 0, 20); // jan/2026
  it('previousCompetence vira o ano', () => {
    expect(previousCompetence(now)).toBe('2025-12');
  });
  it('recentCompetences: mês atual + 12 anteriores', () => {
    const list = recentCompetences(13, now);
    expect(list).toHaveLength(13);
    expect(list[0]).toBe('2026-01');
    expect(list[1]).toBe('2025-12');
    expect(list[12]).toBe('2025-01');
  });
  it('competenceLabel', () => {
    expect(competenceLabel('2026-03')).toBe('Março/2026');
    expect(competenceLabel('x')).toBe('x');
  });
});
