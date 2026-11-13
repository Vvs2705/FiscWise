import { useEffect } from 'react';
import { useLocation, Outlet } from 'react-router-dom';
import { Sidebar } from '@/components/Sidebar';
import { Header } from '@/components/Header';
import { TrialBanner } from '@/components/TrialBanner';
import { useAuthStore } from '@/stores/authStore';
import { maybeStartWelcomeTour } from '@/lib/welcomeTour';

export function DashboardLayout() {
  const location = useLocation();
  const role = useAuthStore((state) => state.user?.role);

  // Primeiro acesso do escritório: tour de boas-vindas pelas partes principais.
  // Espera a primeira tela pintar para o tour encontrar o menu e o botão Ajuda.
  useEffect(() => {
    if (!role || role === 'client') return;
    const timer = window.setTimeout(() => void maybeStartWelcomeTour(), 900);
    return () => window.clearTimeout(timer);
  }, [role]);

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
        <Header />
        <TrialBanner />
        {/* key no pathname re-monta o conteúdo e dispara a entrada (fade + 6px, 250 ms) */}
        <main
          key={location.pathname}
          className="page-enter flex-1 overflow-y-auto bg-background p-4 md:p-6"
        >
          <Outlet />
        </main>
      </div>
    </div>
  );
}
