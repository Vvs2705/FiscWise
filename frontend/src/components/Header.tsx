import { useMemo } from 'react';
import { useLocation } from 'react-router-dom';
import { LogOut, Moon, Sun } from 'lucide-react';
import { useAuthStore } from '@/stores/authStore';
import { useTheme } from '@/lib/hooks/useTheme';
import { Button } from './ui/Button';

/** Títulos das rotas reais do App. Subrotas herdam pelo prefixo (ex.: /clientes/:id). */
const sectionTitles: ReadonlyArray<readonly [string, string]> = [
  ['/painel', 'Painel'],
  ['/foco', 'Foco de hoje'],
  ['/clientes', 'Clientes'],
  ['/fechamento', 'Fechamento mensal'],
  ['/obrigacoes', 'Obrigações'],
  ['/documentos', 'Documentos'],
  ['/notas-fiscais', 'Notas fiscais'],
  ['/ecac', 'Central e-CAC'],
  ['/guias', 'Guias e pagamentos'],
  ['/caixa-postal-fiscal', 'Caixa postal fiscal'],
  ['/procuracoes', 'Procurações'],
  ['/certificados', 'Certificados'],
  ['/financeiro', 'Financeiro'],
  ['/whatsapp', 'WhatsApp'],
  ['/portal', 'Portal do cliente'],
  ['/relatorios', 'Relatórios'],
  ['/aprender', 'Aprender'],
  ['/configuracoes', 'Configurações'],
  ['/calculadora', 'Calculadora fiscal'],
];

function getSectionTitle(pathname: string): string {
  const match = sectionTitles.find(
    ([prefix]) => pathname === prefix || pathname.startsWith(`${prefix}/`),
  );
  return match?.[1] ?? 'FiscWise';
}

function ThemeToggle() {
  const { theme, toggle } = useTheme();
  const isDark = theme === 'dark';

  return (
    <button
      type="button"
      onClick={toggle}
      aria-label={isDark ? 'Ativar modo claro' : 'Ativar modo escuro'}
      title={isDark ? 'Modo claro' : 'Modo escuro'}
      className="flex h-9 w-9 items-center justify-center rounded-md text-muted-foreground transition-colors duration-100 hover:bg-muted hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
    >
      {isDark ? <Sun className="h-[18px] w-[18px]" aria-hidden="true" /> : <Moon className="h-[18px] w-[18px]" aria-hidden="true" />}
    </button>
  );
}

export function Header() {
  const { user, logout } = useAuthStore();
  const location = useLocation();

  const sectionTitle = useMemo(() => getSectionTitle(location.pathname), [location.pathname]);

  /* Iniciais do nome do usuário para o avatar */
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
    <header className="flex h-14 shrink-0 items-center justify-between gap-3 border-b border-border bg-card px-4 md:px-6">
      {/* Esquerda: título da seção */}
      <h2 className="min-w-0 truncate text-base font-semibold text-foreground">{sectionTitle}</h2>

      {/* Direita: controles */}
      <div className="flex shrink-0 items-center gap-1 sm:gap-2">
        <ThemeToggle />

        <div className="mx-1 hidden h-6 w-px bg-border sm:block" aria-hidden="true" />

        {/* Usuário */}
        <div className="flex min-w-0 items-center gap-2">
          <div
            className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary/10 text-xs font-semibold text-primary"
            aria-hidden="true"
          >
            {initials}
          </div>
          {user?.email && (
            <span className="hidden max-w-48 truncate text-sm text-muted-foreground lg:inline">
              {user.email}
            </span>
          )}
        </div>

        <Button
          variant="ghost"
          size="sm"
          onClick={() => logout()}
          aria-label="Sair da conta"
          className="text-muted-foreground hover:text-foreground"
        >
          <LogOut className="h-4 w-4" aria-hidden="true" />
          <span className="hidden sm:inline">Sair</span>
        </Button>
      </div>
    </header>
  );
}
