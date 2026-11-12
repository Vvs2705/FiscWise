import { useLocation, Outlet } from 'react-router-dom';
import { Sidebar } from '@/components/Sidebar';
import { Header } from '@/components/Header';

export function DashboardLayout() {
  const location = useLocation();

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
        <Header />
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
