/**
 * Extensão do arquivo a partir da URL (ignorando query string e fragmento).
 *
 * A API devolve `file_url` como URL assinada (`...arquivo.pdf?token=...`),
 * então `endsWith('.pdf')` direto na URL não funciona mais.
 */
export function fileExtension(url: string | null | undefined): string {
  if (!url) return '';
  const path = url.split('#', 1)[0].split('?', 1)[0];
  const last = path.slice(path.lastIndexOf('/') + 1);
  const dot = last.lastIndexOf('.');
  return dot > 0 ? last.slice(dot + 1).toLowerCase() : '';
}

const IMAGE_EXTS = new Set(['png', 'jpg', 'jpeg', 'gif', 'webp']);

export function isPdfUrl(url: string | null | undefined): boolean {
  return fileExtension(url) === 'pdf';
}

export function isImageUrl(url: string | null | undefined): boolean {
  return IMAGE_EXTS.has(fileExtension(url));
}
