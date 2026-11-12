import { describe, expect, it } from 'vitest';
import { fileExtension, isImageUrl, isPdfUrl } from './fileUrl';

describe('fileUrl', () => {
  it('ignora a query string da URL assinada', () => {
    const url = 'https://x.supabase.co/storage/v1/object/sign/documents/t/abc.PDF?token=eyJ.a.b';
    expect(fileExtension(url)).toBe('pdf');
    expect(isPdfUrl(url)).toBe(true);
    expect(isImageUrl(url)).toBe(false);
  });

  it('reconhece imagem e lida com vazio', () => {
    expect(isImageUrl('https://h/a/foto.jpeg#x')).toBe(true);
    expect(fileExtension(null)).toBe('');
    expect(fileExtension('https://h/sem-extensao?x=1.pdf')).toBe('');
  });
});
