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
  ['/forgot-password', 'Recuperar senha'],
  ['/reset-password', 'Redefinir senha'],
  ['/portal/login', 'Portal do Cliente'],
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

export function RouteTitle() {
  const { pathname } = useLocation();

  useEffect(() => {
    document.title = resolveTitle(pathname);
  }, [pathname]);

  return null;
}
