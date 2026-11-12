import { lazy, Suspense, useEffect, useRef, useState } from 'react';
import { MotionConfig } from 'framer-motion';
import { DashboardLayout } from '@/layouts/DashboardLayout';
import { useAuthStore } from '@/stores/authStore';

// cmdk + Radix Dialog + lista de clientes (~19 kB gz): só baixa dentro do app
// autenticado e só monta no primeiro Ctrl+K / Cmd+K.
const loadCommandMenu = () => import('@/components/ui/CommandMenu');
const CommandMenu = lazy(() => loadCommandMenu().then((m) => ({ default: m.CommandMenu })));

const isCommandShortcut = (e: KeyboardEvent) => e.key === 'k' && (e.metaKey || e.ctrlKey);

/**
 * Montado junto com o CommandMenu (mesmo Suspense, depois dele): reenvia o
 * atalho que "armou" o menu para que ele já abra no primeiro Ctrl+K.
 * O ref evita reenviar duas vezes no StrictMode (o menu alterna a cada atalho).
 */
function ReplayShortcut() {
  const done = useRef(false);
  useEffect(() => {
    if (done.current) return;
    done.current = true;
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'k', ctrlKey: true }));
  }, []);
  return null;
}

// Busca global (Ctrl+K) lista clientes e rotas da equipe: não existe para o
// cliente do portal, que levaria 403 e cairia em telas que não pode abrir.
function StaffCommandMenu() {
  const role = useAuthStore((state) => state.user?.role);
  const [armed, setArmed] = useState(false);
  const isClient = role === 'client';

  useEffect(() => {
    if (isClient || armed) return;
    const onKey = (e: KeyboardEvent) => {
      if (!isCommandShortcut(e)) return;
      e.preventDefault();
      setArmed(true);
    };
    document.addEventListener('keydown', onKey);
    // Pré-carrega o chunk em tempo ocioso para o primeiro Ctrl+K ser instantâneo.
    const idle = window.requestIdleCallback
      ? window.requestIdleCallback(() => void loadCommandMenu(), { timeout: 8000 })
      : window.setTimeout(() => void loadCommandMenu(), 4000);
    return () => {
      document.removeEventListener('keydown', onKey);
      if (window.cancelIdleCallback) window.cancelIdleCallback(idle);
      else window.clearTimeout(idle);
    };
  }, [isClient, armed]);

  if (isClient || !armed) return null;
  return (
    <Suspense fallback={null}>
      <CommandMenu />
      <ReplayShortcut />
    </Suspense>
  );
}

/**
 * Casca do app autenticado (carregada sob demanda a partir do App.tsx).
 * Concentra o que as rotas públicas não precisam: framer-motion (MotionConfig),
 * Sidebar/Header (via DashboardLayout) e a busca global. Assim /login,
 * /register, /termos e /privacidade não baixam nada disso.
 */
export default function AppShell() {
  return (
    <MotionConfig reducedMotion="user">
      <StaffCommandMenu />
      <DashboardLayout />
    </MotionConfig>
  );
}
