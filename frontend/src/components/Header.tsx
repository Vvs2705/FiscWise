import { useMemo } from 'react';
import { useLocation } from 'react-router-dom';
import { LogOut, User } from 'lucide-react';
import { useAuthStore } from '@/stores/authStore';
import { Button } from './ui/Button';

const sectionTitles: Record<string, string> = {
  '/dashboard': 'Dashboard operacional',
  '/clientes': 'Clientes',
  '/documentos': 'Documentos',
  '/agenda-prazos': 'Agenda e prazos',
  '/certificados': 'Certificados digitais',
  '/financeiro': 'Financeiro',
  '/configuracoes': 'Configurações',
};

export function Header() {
  const { user, logout } = useAuthStore();
  const location = useLocation();
  const sectionTitle = useMemo(() => {
    return sectionTitles[location.pathname] ?? 'FiscWise';
  }, [location.pathname]);

  return (
    <header className="flex h-16 items-center justify-between gap-3 border-b bg-card px-4 md:px-6">
      <div className="min-w-0">
        <p className="truncate text-sm text-muted-foreground">
          Bem-vindo, {user?.full_name || 'Usuário'}
        </p>
        <h2 className="truncate text-base font-semibold md:text-lg">{sectionTitle}</h2>
      </div>
      <div className="flex shrink-0 items-center gap-2 md:gap-4">
        <div className="hidden items-center gap-2 text-sm text-muted-foreground sm:flex">
          <User className="h-4 w-4" />
          <span className="max-w-56 truncate">{user?.email}</span>
        </div>
        <Button variant="ghost" size="sm" onClick={logout} aria-label="Sair da conta">
          <LogOut className="mr-2 h-4 w-4" />
          <span className="hidden sm:inline">Sair</span>
        </Button>
      </div>
    </header>
  );
}
