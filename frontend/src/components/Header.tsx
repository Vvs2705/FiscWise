import { useMemo } from 'react';
import { useLocation } from 'react-router-dom';
import { LogOut, Moon, Sun, User } from 'lucide-react';
import { useAuthStore } from '@/stores/authStore';
import { useTheme } from '@/lib/hooks/useTheme';
import { Button } from './ui/Button';
import { cn } from '@/lib/utils';

const sectionTitles: Record<string, string> = {
  '/dashboard':      'Painel',
  '/clientes':       'Clientes',
  '/documentos':     'Documentos',
  '/agenda-prazos':  'Agenda Fiscal',
  '/certificados':   'Certificados',
  '/financeiro':     'Financeiro',
  '/calculadora':    'Calculadora Fiscal',
  '/das-mensal':     'Guias e DAS',
  '/obrigacoes':     'Obrigações',
  '/configuracoes':  'Configurações',
};

function ThemeToggle() {
  const { theme, toggle } = useTheme();

  return (
    <button
      onClick={toggle}
      aria-label={theme === 'dark' ? 'Ativar modo claro' : 'Ativar modo escuro'}
      className={cn(
        'relative flex h-9 w-16 items-center rounded-full p-1',
        'transition-all duration-300 ease-spring',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
        theme === 'dark'
          ? 'bg-primary/20 ring-1 ring-primary/30'
          : 'bg-muted ring-1 ring-border',
      )}
    >
      {/* Bolinha deslizante */}
      <span
        className={cn(
          'flex h-7 w-7 items-center justify-center rounded-full shadow-sm',
          'transition-all duration-300 ease-spring',
          theme === 'dark'
            ? 'translate-x-7 bg-primary text-primary-foreground'
            : 'translate-x-0 bg-white text-foreground',
        )}
      >
        {theme === 'dark' ? (
          <Moon className="h-3.5 w-3.5" />
        ) : (
          <Sun className="h-3.5 w-3.5" />
        )}
      </span>
    </button>
  );
}

export function Header() {
  const { user, logout } = useAuthStore();
  const location = useLocation();

  const sectionTitle = useMemo(
    () => sectionTitles[location.pathname] ?? 'FiscWise',
    [location.pathname],
  );

  /* Inicial do nome do usuário para o avatar */
  const initials = useMemo(() => {
    const name = user?.full_name ?? user?.email ?? '';
    return name
      .split(' ')
      .filter(Boolean)
      .slice(0, 2)
      .map((w) => w[0].toUpperCase())
      .join('');
  }, [user]);

  return (
    <header className="flex h-16 items-center justify-between gap-3 border-b bg-card px-4 md:px-6 animate-fade-in">
      {/* Esquerda: título da seção */}
      <div className="min-w-0">
        <p className="text-xs text-muted-foreground">
          Sua rotina fiscal começa aqui, {user?.full_name?.split(' ')[0] || 'contador'}
        </p>
        <h2 className="truncate text-base font-semibold md:text-lg">{sectionTitle}</h2>
      </div>

      {/* Direita: controles */}
      <div className="flex shrink-0 items-center gap-2 md:gap-3">
        {/* Toggle de tema */}
        <ThemeToggle />

        {/* Email (desktop) */}
        <div className="hidden items-center gap-2 text-sm text-muted-foreground sm:flex">
          <User className="h-4 w-4 shrink-0" />
          <span className="max-w-48 truncate">{user?.email}</span>
        </div>

        {/* Avatar com inicial */}
        <div
          className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary/10 text-xs font-semibold text-primary ring-1 ring-primary/20"
          aria-hidden="true"
        >
          {initials}
        </div>

        {/* Botão sair */}
        <Button
          variant="secondary"
          size="sm"
          onClick={logout}
          aria-label="Sair da conta"
          className="text-muted-foreground hover:text-foreground"
        >
          <LogOut className="h-4 w-4" />
          <span className="hidden sm:inline">Sair</span>
        </Button>
      </div>
    </header>
  );
}
