import { describe, expect, it } from 'vitest';
import { importClientRows, parseClientRows } from './xlsxImport';

const HEADER = [
  'Nome / Razao Social', 'CPF / CNPJ', 'Tipo (PJ ou PF)', 'Regime Tributario',
  'E-mail', 'Telefone', 'Inscricao Municipal', 'Inscricao Estadual', 'Observacoes',
];

describe('parseClientRows', () => {
  it('mapeia todas as linhas, ignora exemplo e linhas vazias', () => {
    const rows = parseClientRows([
      HEADER,
      ['Empresa Exemplo Ltda', '12.345.678/0001-90', 'PJ', 'Simples Nacional', 'contato@exemplo.com.br', '', '', '', ''],
      ['Padaria Sol Ltda', '11.222.333/0001-81', 'PJ', 'Simples Nacional', 'sol@padaria.com', '(11) 1234-5678', '', '', 'obs'],
      [null, null, null, null, null, null, null, null, null],
      ['Maria Souza', '529.982.247-25', '', '', '', '', '', '', ''],
    ]);
    expect(rows).toHaveLength(2);
    expect(rows[0]).toMatchObject({ rowNumber: 3, payload: { name: 'Padaria Sol Ltda', entity_type: 'pj', tax_regime: 'Simples Nacional', notes: 'obs', status: 'active' } });
    expect(rows[1]).toMatchObject({ rowNumber: 5, payload: { name: 'Maria Souza', entity_type: 'pf' } });
  });

  it('marca erro por linha sem descartar as outras', () => {
    const rows = parseClientRows([
      HEADER,
      ['', '11.222.333/0001-81', 'PJ', '', '', '', '', '', ''],
      ['Cliente X', '123', 'PJ', '', '', '', '', '', ''],
      ['Cliente Y', '', 'PJ', '', 'email-ruim', '', '', '', ''],
      ['Cliente Z', '', 'PJ', '', '', '', '', '', ''],
    ]);
    expect(rows.map((r) => Boolean(r.error))).toEqual([true, true, true, false]);
  });

  it('cabeçalho errado vira erro único', () => {
    expect(parseClientRows([['A', 'B'], ['x', 'y']])[0].error).toMatch(/Cabeçalho/);
  });
});

describe('importClientRows', () => {
  it('continua depois de um erro e reporta cada linha', async () => {
    const parsed = parseClientRows([
      HEADER,
      ['Cliente A', '', 'PJ', '', '', '', '', '', ''],
      ['Cliente B', '', 'PJ', '', '', '', '', '', ''],
      ['', '', '', '', 'x@y.com', '', '', '', ''],
      ['Cliente C', '', 'PJ', '', '', '', '', '', ''],
    ]);
    const created: string[] = [];
    const results = await importClientRows(
      parsed,
      async (p) => {
        if (p.name === 'Cliente B') throw new Error('duplicado');
        created.push(p.name);
      },
      (e) => (e as Error).message,
    );
    expect(created).toEqual(['Cliente A', 'Cliente C']);
    expect(results.map((r) => [r.rowNumber, r.ok, r.message])).toEqual([
      [2, true, 'Cadastrado'],
      [3, false, 'duplicado'],
      [4, false, 'Nome / Razão Social obrigatório.'],
      [5, true, 'Cadastrado'],
    ]);
  });
});
