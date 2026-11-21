import { describe, expect, it } from 'vitest';
import { invoiceSchema, issuerSchema } from './invoice.schema';

// Garante que o z.preprocess e as mensagens continuam iguais depois do zod 4.
const base = {
  issuer_id: '3f2b8a1e-5c4d-4e6f-8a9b-0c1d2e3f4a5b',
  valor_servico: 'R$ 1.500,50',
  descricao_servico: 'Consultoria fiscal',
  competencia: '2026-11',
  tomador_nome: 'Empresa X',
  tomador_cpf_cnpj: '01290000000136',
  tomador_email: '',
  tomador_municipio_ibge: '3550308',
};

describe('invoiceSchema (zod 4)', () => {
  it('converte valores em texto e trata campos vazios', () => {
    const out = invoiceSchema.parse({ ...base, valor_servico: '1500,50', client_id: '', valor_deducoes: '' });
    expect(out.valor_servico).toBe(1500.5);
    expect(out.valor_deducoes).toBe(0);
    expect(out.client_id).toBeUndefined();
  });

  it('mantém as mensagens em português', () => {
    const r = invoiceSchema.safeParse({ ...base, valor_servico: '0', tomador_email: 'x@' });
    expect(r.success).toBe(false);
    const msgs = r.success ? [] : r.error.issues.map((i) => i.message);
    expect(msgs).toContain('O valor do serviço deve ser maior que zero');
    expect(msgs).toContain('E-mail inválido');
  });
});

describe('issuerSchema (zod 4)', () => {
  it('alíquota vazia vira undefined e retenção tem padrão false', () => {
    const out = issuerSchema.parse({ cnpj: '01290000000136', regime_tributario: 'simples', municipio_ibge: '3550308', aliquota_iss: '' });
    expect(out.aliquota_iss).toBeUndefined();
    expect(out.retencao_iss).toBe(false);
  });
});
