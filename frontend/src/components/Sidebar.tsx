import { Link, useLocation } from 'react-router-dom';
import {
  CalendarClock,
  FolderKanban,
  LayoutDashboard,
  ReceiptText,
  Settings,
  ShieldCheck,
  UsersRound,
  Calculator,
  Coins,
  ListChecks,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Logo } from '@/components/Logo';

const navigation = [
  { name: 'Painel',             href: '/dashboard',      icon: LayoutDashboard },
  { name: 'Clientes',           href: '/clientes',       icon: UsersRound },
  { name: 'Agenda Fiscal',      href: '/agenda-prazos',  icon: CalendarClock },
  { name: 'Obrigações',         href: '/obrigacoes',     icon: ListChecks },
  { name: 'Documentos',         href: '/documentos',     icon: FolderKanban },
  { name: 'Guias e DAS',        href: '/das-mensal',     icon: Coins },
  { name: 'Certificados',       href: '/certificados',   icon: ShieldCheck },
  { name: 'Financeiro',         href: '/financeiro',     icon: ReceiptText },
  { name: 'Calculadora',        href: '/calculadora',    icon: Calculator },
  { name: 'Configurações',      href: '/configuracoes',  icon: Settings },
];


export function Sidebar() {
  const location = useLocation();

  return (
    <aside
      className={cn(
        'flex h-full w-16 shrink-0 flex-col md:w-64',
        'bg-sidebar border-r border-sidebar-border',
        'transition-all duration-300 ease-spring',
      )}
    >
      {/* Logo — clicável, retorna ao dashboard */}
      <Link
        to="/dashboard"
        aria-label="Ir para o dashboard"
        className="flex h-16 items-center justify-center border-b border-sidebar-border px-3 transition-opacity hover:opacity-80 md:justify-start md:px-5"
      >
        {/* Desktop: logo completo */}
        <div className="hidden md:block">
          <Logo variant="full" theme="dark" size={34} />
        </div>
        {/* Mobile: só ícone */}
        <div className="md:hidden">
          <Logo variant="icon" size={32} />
        </div>
      </Link>

      {/* Nav */}
      <nav className="flex-1 space-y-0.5 overflow-y-auto px-2 py-4">
        <div className="mb-3 hidden px-3 md:block">
          <p className="text-[10px] font-semibold uppercase tracking-[0.24em] text-sidebar-muted">
            Central do contador
          </p>
        </div>
        {navigation.map((item, i) => {
          const isActive =
            location.pathname === item.href ||
            location.pathname.startsWith(`${item.href}/`);

          return (
            <Link
              key={item.name}
              to={item.href}
              aria-label={item.name}
              title={item.name}
              style={{ animationDelay: `${i * 35}ms` }}
              className={cn(
                'animate-slide-in-left',
                'group relative flex items-center justify-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium',
                'transition-all duration-150 ease-spring md:justify-start',
                isActive
                  ? [
                      'bg-sidebar-active-bg text-sidebar-active-fg shadow-sm',
                      'before:absolute before:left-0 before:top-1/2 before:h-5 before:w-[3px]',
                      'before:-translate-y-1/2 before:rounded-r-full before:bg-white/60',
                    ]
                  : [
                      'text-sidebar-muted',
                      'hover:bg-sidebar-hover-bg hover:text-sidebar-foreground',
                    ],
              )}
            >
              <item.icon
                className={cn(
                  'h-[18px] w-[18px] shrink-0 transition-transform duration-150',
                  'group-hover:scale-110',
                  isActive ? 'text-sidebar-active-fg' : 'text-sidebar-muted',
                )}
              />
              <span className="hidden truncate md:inline">{item.name}</span>

              {/* Tooltip no mobile */}
              <span className="pointer-events-none absolute left-full ml-2 hidden whitespace-nowrap rounded-md bg-popover px-2 py-1 text-xs text-popover-foreground shadow-md group-hover:block md:hidden">
                {item.name}
              </span>
            </Link>
          );
        })}
      </nav>

      {/* Rodapé da sidebar */}
      <div className="border-t border-sidebar-border px-2 py-3">
        {/* Desktop: branding + link Vstack */}
        <div className="hidden flex-col gap-2 px-3 py-1 md:flex">
          <div className="flex items-center gap-2">
            <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-md bg-sidebar-accent/20 text-[10px] font-bold text-sidebar-accent">
              FW
            </div>
            <div className="min-w-0">
              <p className="truncate text-xs font-medium text-sidebar-foreground">FiscWise</p>
              <p className="truncate text-[10px] text-sidebar-muted">Fiscal Intelligence OS</p>
            </div>
          </div>
          <div className="rounded-xl border border-white/10 bg-white/5 px-3 py-2">
            <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-sidebar-muted">Posicionamento</p>
            <p className="mt-1 text-xs leading-relaxed text-sidebar-foreground/90">
              Organize sua carteira, acompanhe prazos e atenda seus clientes com mais precisão.
            </p>
          </div>
        </div>

        {/* Mobile: só tooltip com crédito */}
        <div className="flex items-center justify-center md:hidden">
          <a
            href="https://vstack-solutions.com.br"
            target="_blank"
            rel="noopener noreferrer"
            title="by Vstack Solutions"
            className="flex h-7 w-7 items-center justify-center rounded-md text-sidebar-muted transition-colors hover:text-sidebar-foreground"
          >
            <svg viewBox="0 0 16 16" fill="none" className="h-3.5 w-3.5" aria-hidden="true">
              <circle cx="8" cy="8" r="7" stroke="currentColor" strokeWidth="1.5"/>
              <path d="M8 4v4l2.5 2.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
            </svg>
          </a>
        </div>
      </div>
    </aside>
  );
}
