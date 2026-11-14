import { describe, expect, it } from 'vitest';
import {
  ajusteEstruturado,
  formatarTamanho,
  montarCorpoAjuste,
  regiaoLabel,
  statusLabel,
  validarAjuste,
  validarArquivo,
  type AjusteFiscalInput,
} from './ajustesFiscais';
import { normalizarAjustesAtivos } from './hooks/useAjustesFiscais';

const base: AjusteFiscalInput = {
  tipo: 'outro',
  uf: 'SP',
  descricao: 'Preciso de um ajuste para o meu município.',
};

describe('validarAjuste', () => {
  it('exige UF e descrição com 10+ caracteres', () => {
    const erros = validarAjuste({ ...base, uf: '', descricao: 'curto' });
    expect(erros.uf).toBeTruthy();
    expect(erros.descricao).toBeTruthy();
  });

  it('aceita "outro" só com UF e descrição', () => {
    expect(validarAjuste(base)).toEqual({});
  });

  it('feriado exige data', () => {
    expect(validarAjuste({ ...base, tipo: 'feriado' }).data).toBeTruthy();
    expect(validarAjuste({ ...base, tipo: 'feriado', data: '2026-03-15' })).toEqual({});
  });

  it('prazo exige obrigação e dia de 1 a 31', () => {
    const erros = validarAjuste({ ...base, tipo: 'prazo', due_day: 40 });
    expect(erros.obrigacao_code).toBeTruthy();
    expect(erros.due_day).toBeTruthy();
    expect(validarAjuste({ ...base, tipo: 'prazo', obrigacao_code: 'GIA', due_day: 20 })).toEqual({});
  });

  it('código IBGE, quando informado, tem 7 dígitos', () => {
    expect(validarAjuste({ ...base, municipio_ibge: '123' }).municipio_ibge).toBeTruthy();
    expect(validarAjuste({ ...base, municipio_ibge: '3509502' })).toEqual({});
  });
});

describe('montarCorpoAjuste', () => {
  it('manda só os campos do tipo', () => {
    const corpo = montarCorpoAjuste({
      ...base,
      tipo: 'feriado',
      data: '2026-03-15',
      recorrente_anual: true,
      obrigacao_code: 'GIA',
      due_day: 20,
      municipio_ibge: ' ',
      fonte: '  ',
    });
    expect(corpo).toEqual({
      tipo: 'feriado',
      uf: 'SP',
      descricao: base.descricao,
      data: '2026-03-15',
      recorrente_anual: true,
    });
  });
});

describe('rótulos', () => {
  it('status em português', () => {
    expect(statusLabel('aplicada_no_escritorio')).toBe('Vale no seu escritório');
    expect(statusLabel('em_analise')).toBe('Em análise');
    expect(statusLabel('regra_geral')).toBe('Virou regra geral');
    expect(statusLabel('recusada')).toBe('Recusada');
  });

  it('região: município ou estado todo', () => {
    expect(regiaoLabel({ uf: 'SP', municipio_nome: 'Campinas' })).toBe('Campinas/SP');
    expect(regiaoLabel({ uf: 'BA' })).toBe('BA (estado todo)');
  });

  it('só feriado e prazo valem na hora', () => {
    expect(ajusteEstruturado('feriado')).toBe(true);
    expect(ajusteEstruturado('prazo')).toBe(true);
    expect(ajusteEstruturado('nova_obrigacao')).toBe(false);
    expect(ajusteEstruturado('outro')).toBe(false);
  });
});

describe('arquivos da base de conhecimento', () => {
  it('aceita PDF/DOCX/TXT/MD até 20 MB', () => {
    expect(validarArquivo({ name: 'lei.pdf', size: 1000 })).toBeNull();
    expect(validarArquivo({ name: 'lei.exe', size: 1000 })).toBeTruthy();
    expect(validarArquivo({ name: 'lei.pdf', size: 21 * 1024 * 1024 })).toBeTruthy();
    expect(validarArquivo({ name: 'lei.pdf', size: 0 })).toBeTruthy();
  });

  it('formata o tamanho', () => {
    expect(formatarTamanho(512)).toBe('512 B');
    expect(formatarTamanho(2048)).toBe('2 KB');
    expect(formatarTamanho(1.5 * 1024 * 1024)).toBe('1,5 MB');
  });
});

describe('normalizarAjustesAtivos', () => {
  it('aceita objeto ou lista com escopo', () => {
    const item = { id: '1', escopo: 'geral' } as never;
    const outro = { id: '2', escopo: 'escritorio' } as never;
    expect(normalizarAjustesAtivos([item, outro])).toEqual({ escritorio: [outro], gerais: [item] });
    expect(normalizarAjustesAtivos({ escritorio: [outro] })).toEqual({ escritorio: [outro], gerais: [] });
    expect(normalizarAjustesAtivos(null)).toEqual({ escritorio: [], gerais: [] });
  });
});
