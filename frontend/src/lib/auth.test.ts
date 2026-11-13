import { describe, expect, it } from 'vitest';
import {
  documentoValido,
  formatarDocumento,
  mensagemErroDocumento,
  newPasswordError,
  somenteDigitos,
} from './auth';

describe('newPasswordError', () => {
  it('exige ao menos 8 caracteres, como o cadastro', () => {
    expect(newPasswordError('1234567')).toMatch(/8 caracteres/);
    expect(newPasswordError('12345678')).toBeNull();
  });

  it('recusa senha acima de 72 bytes (limite do bcrypt), contando acentos', () => {
    expect(newPasswordError('a'.repeat(72))).toBeNull();
    expect(newPasswordError('ç'.repeat(37))).toMatch(/72 bytes/); // 74 bytes
  });
});

describe('CNPJ/CPF do cadastro (um teste grátis por documento)', () => {
  it('aceita CNPJ e CPF válidos, com ou sem máscara', () => {
    expect(documentoValido('01.290.000/0001-36')).toBe(true);
    expect(documentoValido('01290000000136')).toBe(true);
    expect(documentoValido('529.982.247-25')).toBe(true);
    expect(documentoValido('52998224725')).toBe(true);
  });

  it('recusa dígito verificador errado, tamanho errado e sequência repetida', () => {
    expect(documentoValido('01.290.000/0001-37')).toBe(false);
    expect(documentoValido('529.982.247-24')).toBe(false);
    expect(documentoValido('123')).toBe(false);
    expect(documentoValido('00000000000000')).toBe(false);
    expect(documentoValido('11111111111')).toBe(false);
    expect(documentoValido('')).toBe(false);
  });

  it('formata enquanto digita e limpa para enviar', () => {
    expect(formatarDocumento('52998224725')).toBe('529.982.247-25');
    expect(formatarDocumento('01290000000136')).toBe('01.290.000/0001-36');
    expect(formatarDocumento('0129')).toBe('012.9');
    expect(somenteDigitos('01.290.000/0001-36')).toBe('01290000000136');
  });

  it('traduz os códigos de erro do backend', () => {
    expect(mensagemErroDocumento('INVALID_DOCUMENT')).toMatch(/inválido/);
    expect(mensagemErroDocumento('DOCUMENT_ALREADY_USED')).toMatch(/já tem uma conta/);
    expect(mensagemErroDocumento('EMAIL_ALREADY_EXISTS')).toBeNull();
  });
});
