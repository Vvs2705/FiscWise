import { describe, expect, it } from 'vitest';
import {
  CERTIFICADO_MAX_BYTES,
  certificadoUtilizavel,
  dataBR,
  diasAte,
  formatarDocumentoCertificado,
  pendenciasDoErro,
  seloCertificado,
  validarEnvioCertificado,
  type CertificadoCofre,
} from './certificados';

const arquivo = (name: string, size = 4000) => ({ name, size });

describe('validarEnvioCertificado', () => {
  it('exige arquivo', () => {
    expect(validarEnvioCertificado({ arquivo: null, senha: 'x', escopo: 'escritorio' })).toMatch(/Escolha o arquivo/);
  });

  it('aceita .pfx e .p12 (maiúsculas também)', () => {
    expect(validarEnvioCertificado({ arquivo: arquivo('empresa.pfx'), senha: 's', escopo: 'escritorio' })).toBeNull();
    expect(validarEnvioCertificado({ arquivo: arquivo('EMPRESA.P12'), senha: 's', escopo: 'escritorio' })).toBeNull();
  });

  it('recusa outras extensões e avisa sobre A3', () => {
    expect(validarEnvioCertificado({ arquivo: arquivo('cert.cer'), senha: 's', escopo: 'escritorio' })).toMatch(/A3/);
  });

  it('recusa arquivo vazio ou grande demais', () => {
    expect(validarEnvioCertificado({ arquivo: arquivo('a.pfx', 0), senha: 's', escopo: 'escritorio' })).toMatch(/vazio/);
    expect(
      validarEnvioCertificado({ arquivo: arquivo('a.pfx', CERTIFICADO_MAX_BYTES + 1), senha: 's', escopo: 'escritorio' }),
    ).toMatch(/50 KB/);
  });

  it('exige senha', () => {
    expect(validarEnvioCertificado({ arquivo: arquivo('a.pfx'), senha: '   ', escopo: 'escritorio' })).toMatch(/senha/);
  });

  it('certificado de cliente exige o cliente', () => {
    expect(validarEnvioCertificado({ arquivo: arquivo('a.pfx'), senha: 's', escopo: 'cliente' })).toMatch(/cliente/);
    expect(
      validarEnvioCertificado({ arquivo: arquivo('a.pfx'), senha: 's', escopo: 'cliente', clientId: 'c1' }),
    ).toBeNull();
  });
});

describe('formatação', () => {
  it('formata CNPJ e CPF', () => {
    expect(formatarDocumentoCertificado('11222333000181')).toBe('11.222.333/0001-81');
    expect(formatarDocumentoCertificado('12345678909')).toBe('123.456.789-09');
    expect(formatarDocumentoCertificado(null)).toBe('—');
  });

  it('data no padrão brasileiro', () => {
    expect(dataBR('2027-03-05')).toBe('05/03/2027');
    expect(dataBR('2027-03-05T10:00:00Z')).toBe('05/03/2027');
    expect(dataBR(null)).toBe('—');
  });

  it('conta dias de calendário', () => {
    const hoje = new Date('2026-11-17T15:00:00');
    expect(diasAte('2026-11-17', hoje)).toBe(0);
    expect(diasAte('2026-11-20', hoje)).toBe(3);
    expect(diasAte('2026-11-16', hoje)).toBe(-1);
  });
});

describe('seloCertificado', () => {
  const base = { status: 'valido' as const, valido_ate: '2027-12-31' };

  it('válido, vencendo, vencido, bloqueado', () => {
    expect(seloCertificado({ ...base, dias_para_vencer: 200 })).toEqual({ label: 'Válido', tom: 'success' });
    expect(seloCertificado({ ...base, dias_para_vencer: 30 })).toEqual({ label: 'Vence em 30 dias', tom: 'warning' });
    expect(seloCertificado({ ...base, dias_para_vencer: 1 }).label).toBe('Vence em 1 dia');
    expect(seloCertificado({ ...base, dias_para_vencer: 0 }).tom).toBe('danger');
    expect(seloCertificado({ ...base, status: 'vencido', dias_para_vencer: -3 }).label).toBe('Vencido');
    expect(seloCertificado({ ...base, status: 'bloqueado', dias_para_vencer: 100 }).label).toBe('Bloqueado');
  });

  it('sem dias_para_vencer, calcula pela data', () => {
    const hoje = new Date('2026-11-17T08:00:00');
    expect(seloCertificado({ ...base, valido_ate: '2026-11-27', dias_para_vencer: null }, hoje).label).toBe(
      'Vence em 10 dias',
    );
  });

  it('só certificado válido e não vencido é utilizável', () => {
    const cert = {
      id: '1', escopo: 'cliente', client_id: 'c', titular_nome: 'X', documento: '11222333000181',
      tipo_documento: 'cnpj', emissor: 'AC', valido_ate: '2027-12-31', status: 'valido',
      ultimo_uso: null, created_at: '2026-11-17', dias_para_vencer: 400,
    } as CertificadoCofre;
    expect(certificadoUtilizavel(cert)).toBe(true);
    expect(certificadoUtilizavel({ ...cert, status: 'bloqueado' })).toBe(false);
    expect(certificadoUtilizavel({ ...cert, dias_para_vencer: -1 })).toBe(false);
  });
});

describe('pendenciasDoErro', () => {
  it('lê lista, objeto e texto', () => {
    expect(pendenciasDoErro(['a', 'b'])).toEqual(['a', 'b']);
    expect(pendenciasDoErro({ pendencias: ['Certificado vencido'] })).toEqual(['Certificado vencido']);
    expect(pendenciasDoErro('Falta certificado; Falta teste')).toEqual(['Falta certificado', 'Falta teste']);
    expect(pendenciasDoErro(undefined)).toEqual([]);
  });
});
