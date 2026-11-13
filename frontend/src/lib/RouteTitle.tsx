import { useEffect } from 'react';
import { matchPath, useLocation } from 'react-router-dom';

/**
 * Per-route document title management.
 *
 * The SPA only had the static <title> from index.html, so every internal
 * screen showed the same brand title (bad for browser
 * tabs, history and bookmarks — CORRECOES.md, audit of internal routes).
 *
 * This component maps the current pathname to a friendly title and updates
 * document.title on navigation. Patterns are evaluated in order, so more
 * specific routes must come before their dynamic-segment counterparts.
 */
const SUFFIX = 'FiscWise';

/** Título da página inicial pública (e fallback de marca). */
export const HOME_TITLE = 'FiscWise — Gestão de obrigações fiscais e carteira de clientes para contadores';

const ROUTE_TITLES: ReadonlyArray<readonly [string, string]> = [
  // Public
  ['/login', 'Entrar'],
  ['/register', 'Criar conta'],
  ['/concluir-cadastro', 'Concluir cadastro'],
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
  ['/minicurso', 'Minicurso FiscWise'],
  ['/configuracoes', 'Configurações'],
  ['/sincronizacao', 'Sincronização'],
  ['/calculadora', 'Calculadora Fiscal'],
];

export function resolveTitle(pathname: string): string {
  if (pathname === '/') return HOME_TITLE;
  for (const [pattern, label] of ROUTE_TITLES) {
    if (matchPath({ path: pattern, end: true }, pathname)) {
      return `${label} · ${SUFFIX}`;
    }
  }
  // Fallback: keep the brand title for unmapped routes.
  return HOME_TITLE;
}

const SITE = 'https://www.fiscwise.com.br';

/** Páginas públicas indexáveis: caminho → descrição única. */
const PUBLIC_META: Readonly<Record<string, string>> = {
  '/': 'Gestão de obrigações fiscais e carteira de clientes para contadores e escritórios contábeis: calendário de obrigações, documentos, portal do cliente, guias e fechamento mensal com dossiê em PDF.',
  '/login': 'Entre no FiscWise, a central do contador: obrigações fiscais, documentos, portal do cliente, guias e fechamento mensal de cada cliente em um só lugar.',
  '/register': 'Crie a conta do seu escritório no FiscWise: carteira de clientes, obrigações fiscais e prazos, documentos, guias e fechamento mensal em um só lugar, feito para o contador.',
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
