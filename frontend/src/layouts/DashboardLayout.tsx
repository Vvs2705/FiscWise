import { useLocation, Outlet } from 'react-router-dom';
import { Sidebar } from '@/components/Sidebar';
import { Header } from '@/components/Header';

export function DashboardLayout() {
  const location = useLocation();

  return (
    <div className="fiscwise-shell flex h-screen overflow-hidden">
      <Sidebar />
      <div className="flex flex-1 flex-col overflow-hidden">
        <Header />
        {/* key no pathname faz re-mount + animation ao trocar de rota */}
        <main
          key={location.pathname}
          className="fiscwise-grid flex-1 overflow-y-auto bg-background/40 p-5 md:p-6 page-enter"
        >
          <Outlet />
        </main>
      </div>
    </div>
  );
}
