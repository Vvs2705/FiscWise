import { describe, expect, it, vi } from 'vitest';
import { applyRouteMeta } from './RouteTitle';

function fakeDocument() {
  const nodes: Array<{ tag: string; attrs: Record<string, string> }> = [];
  const matchNode = (sel: string) => {
    const m = sel.match(/^(\w+)\[(\w+)="([^"]+)"\]$/)!;
    return nodes.find((n) => n.tag === m[1] && n.attrs[m[2]] === m[3]) ?? null;
  };
  const wrap = (n: { tag: string; attrs: Record<string, string> }) => ({
    ...n,
    setAttribute: (k: string, v: string) => { n.attrs[k] = v; },
  });
  return {
    nodes,
    document: {
      head: {
        querySelector: (s: string) => { const n = matchNode(s); return n ? wrap(n) : null; },
        appendChild: () => undefined,
      },
      createElement: (tag: string) => {
        const n = { tag, attrs: {} as Record<string, string> };
        nodes.push(n);
        return wrap(n);
      },
    },
  };
}

describe('applyRouteMeta', () => {
  it('indexa páginas públicas com canonical próprio', () => {
    const f = fakeDocument();
    vi.stubGlobal('document', f.document);
    applyRouteMeta('/register');
    const robots = f.nodes.find((n) => n.attrs.name === 'robots')!;
    const canon = f.nodes.find((n) => n.attrs.rel === 'canonical')!;
    expect(robots.attrs.content).toContain('index');
    expect(canon.attrs.href).toBe('https://www.fiscwise.com.br/register');
  });

  it('indexa a página inicial pública com canonical na raiz', () => {
    const f = fakeDocument();
    vi.stubGlobal('document', f.document);
    applyRouteMeta('/');
    expect(f.nodes.find((n) => n.attrs.name === 'robots')!.attrs.content).toContain('index, follow');
    expect(f.nodes.find((n) => n.attrs.rel === 'canonical')!.attrs.href).toBe('https://www.fiscwise.com.br/');
  });

  it('marca área autenticada e rotas desconhecidas como noindex', () => {
    const f = fakeDocument();
    vi.stubGlobal('document', f.document);
    applyRouteMeta('/painel');
    expect(f.nodes.find((n) => n.attrs.name === 'robots')!.attrs.content).toBe('noindex, nofollow');
  });
});
