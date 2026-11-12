import { useEffect } from 'react';
import { matchPath, useLocation } from 'react-router-dom';

/**
 * Per-route document title management.
 *
 * The SPA only had the static <title> from index.html, so every internal
 * screen showed "FiscWise — Gestão Contábil Inteligente" (bad for browser
 * tabs, history and bookmarks — CORRECOES.md, audit of internal routes).
 *
 * This component maps the current pathname to a friendly title and updates
 * document.title on navigation. Patterns are evaluated in order, so more
 * specific routes must come before their dynamic-segment counterparts.
 */
const SUFFIX = 'FiscWise';

const ROUTE_TITLES: ReadonlyArray<readonly [string, string]> = [
  // Public
  ['/login', 'Entrar'],
  ['/register', 'Criar conta'],
  ['/portal/login', 'Portal do Cliente'],
  ['/portal/dashboard', 'Meu Portal'],
  ['/termos', 'Termos de Uso'],
  ['/privacidade', 'Privacidade'],

  // Operação diária
  ['/painel', 'Painel'],
  ['/foco', 'Foco do dia'],

  // Gestão
  ['/clientes/:id', 'Cliente'],
  ['/clientes', 'Clientes'],
  ['/fechamento/:id', 'Fechamento'],
  ['/fechamento', 'Fechamentos'],
  ['/obrigacoes', 'Obrigações'],
  ['/documentos', 'Documentos'],

  // Fiscal (mais específico antes do dinâmico)
  ['/notas-fiscais/nova', 'Nova Nota Fiscal'],
  ['/notas-fiscais/:id/emitir', 'Emitir Nota Fiscal'],
  ['/notas-fiscais/:id', 'Nota Fiscal'],
  ['/notas-fiscais', 'Notas Fiscais'],
  ['/ecac', 'e-CAC'],
  ['/guias/:id', 'Guia'],
  ['/guias', 'Guias'],
  ['/caixa-postal-fiscal', 'Caixa Postal Fiscal'],
  ['/procuracoes', 'Procurações'],
  ['/certificados', 'Certificados'],

  // Financeiro & Canais
  ['/financeiro', 'Financeiro'],
  ['/whatsapp', 'WhatsApp'],
  ['/portal', 'Portal do Cliente'],
  ['/relatorios', 'Relatórios'],

  // Sistema
  ['/aprender', 'Aprender'],
  ['/configuracoes', 'Configurações'],
  ['/calculadora', 'Calculadora Fiscal'],
];

export function resolveTitle(pathname: string): string {
  for (const [pattern, label] of ROUTE_TITLES) {
    if (matchPath({ path: pattern, end: true }, pathname)) {
      return `${label} · ${SUFFIX}`;
    }
  }
  // Fallback: keep the brand title for unmapped routes.
  return `${SUFFIX} — Gestão Contábil Inteligente`;
}

const SITE = 'https://www.fiscwise.com.br';

/** Páginas públicas indexáveis: caminho → descrição única. */
const PUBLIC_META: Readonly<Record<string, string>> = {
  '/login': 'Entre no FiscWise, o sistema de gestão contábil para contadores e escritórios: clientes, prazos fiscais, guias e documentos em um só lugar.',
  '/register': 'Crie sua conta no FiscWise e organize clientes, obrigações fiscais, guias, certificados e financeiro do seu escritório contábil.',
  '/termos': 'Termos de uso do FiscWise, sistema de gestão contábil da Vstack Solutions.',
  '/privacidade': 'Política de privacidade do FiscWise: como tratamos dados pessoais conforme a LGPD.',
};

function upsertMeta(selector: string, create: () => HTMLElement): HTMLElement {
  let el = document.head.querySelector<HTMLElement>(selector);
  if (!el) {
    el = create();
    document.head.appendChild(el);
  }
  return el;
}

function setNamedMeta(name: string, content: string) {
  const el = upsertMeta(`meta[name="${name}"]`, () => {
    const m = document.createElement('meta');
    m.setAttribute('name', name);
    return m;
  });
  el.setAttribute('content', content);
}

function setCanonical(href: string) {
  const el = upsertMeta('link[rel="canonical"]', () => {
    const l = document.createElement('link');
    l.setAttribute('rel', 'canonical');
    return l;
  });
  el.setAttribute('href', href);
}

/** Atualiza robots/canonical/description conforme a rota (Google renderiza JS). */
export function applyRouteMeta(pathname: string) {
  const description = PUBLIC_META[pathname];
  if (description) {
    setNamedMeta('robots', 'index, follow, max-image-preview:large');
    setNamedMeta('description', description);
    setCanonical(`${SITE}${pathname}`);
  } else {
    // Área autenticada, portal e rotas inexistentes: fora do índice.
    setNamedMeta('robots', 'noindex, nofollow');
    setCanonical(`${SITE}/`);
  }
}

export function RouteTitle() {
  const { pathname } = useLocation();

  useEffect(() => {
    document.title = resolveTitle(pathname);
    applyRouteMeta(pathname);
  }, [pathname]);

  return null;
}
