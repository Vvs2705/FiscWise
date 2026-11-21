import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

// O token de sessão fica no localStorage: a CSP bloqueante é a defesa contra XSS.
const headers = readFileSync(resolve(__dirname, '../../public/_headers'), 'utf8');
const csp = headers.match(/^\s*Content-Security-Policy: (.*)$/m)?.[1] ?? '';

describe('CSP do Cloudflare Pages', () => {
  it('está em modo bloqueante, não só relatório', () => {
    expect(csp).not.toBe('');
    expect(headers).not.toMatch(/^\s*Content-Security-Policy-Report-Only:/m);
  });

  it('não libera script inline nem eval, e trava objetos, base e iframes', () => {
    const script = csp.match(/script-src ([^;]*)/)?.[1] ?? '';
    expect(script).not.toContain("'unsafe-inline'");
    expect(script).not.toContain("'unsafe-eval'");
    expect(csp).toContain("object-src 'none'");
    expect(csp).toContain("base-uri 'self'");
    expect(csp).toContain("frame-ancestors 'none'");
  });

  it('libera o que o app usa: login Google, API no Cloud Run e Sentry', () => {
    expect(csp).toMatch(/script-src[^;]*https:\/\/accounts\.google\.com/);
    expect(csp).toMatch(/frame-src[^;]*https:\/\/accounts\.google\.com/);
    expect(csp).toMatch(/connect-src[^;]*https:\/\/\*\.run\.app/);
    expect(csp).toMatch(/connect-src[^;]*ingest\.us\.sentry\.io/);
  });
});
