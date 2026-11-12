import { describe, expect, it } from 'vitest';
import { newPasswordError } from './auth';

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
