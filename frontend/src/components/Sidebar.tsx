import { Link, useLocation } from 'react-router-dom';
import {
  CalendarClock,
  FolderKanban,
  LayoutDashboard,
  ReceiptText,
  Settings,
  ShieldCheck,
  UsersRound,
} from 'lucide-react';
import { cn } from '@/lib/utils';

const navigation = [
  { name: 'Dashboard',      href: '/dashboard',      icon: LayoutDashboard },
  { name: 'Clientes',       href: '/clientes',        icon: UsersRound },
  { name: 'Documentos',     href: '/documentos',      icon: FolderKanban },
  { name: 'Agenda / Prazos',href: '/agenda-prazos',   icon: CalendarClock },
  { name: 'Certificados',   href: '/certificados',    icon: ShieldCheck },
  { name: 'Financeiro',     href: '/financeiro',      icon: ReceiptText },
  { name: 'Configurações',  href: '/configuracoes',   icon: Settings },
];

/* Logo SVG da FiscWise — ícone de gráfico + "FW" */
function FiscWiseLogo({ compact = false }: { compact?: boolean }) {
  return (
    <div className="flex items-center gap-3">
      {/* Ícone */}
      <div className="relative flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-sidebar-accent/20 ring-1 ring-sidebar-accent/30">
        <svg
          viewBox="0 0 36 36"
          fill="none"
          className="h-5 w-5"
          aria-hidden="true"
        >
          {/* Barra esquerda */}
          <rect x="4"  y="20" width="6" height="12" rx="2" fill="hsl(var(--sidebar-logo-accent))" opacity="0.6" />
          {/* Barra central */}
          <rect x="15" y="12" width="6" height="20" rx="2" fill="hsl(var(--sidebar-logo-accent))" opacity="0.85" />
          {/* Barra direita */}
          <rect x="26" y="6"  width="6" height="26" rx="2" fill="hsl(var(--sidebar-logo-accent))" />
          {/* Linha de tendência */}
          <path
            d="M7 18 L18 10 L29 4"
            stroke="hsl(var(--sidebar-logo-accent))"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            opacity="0.5"
          />
        </svg>
      </div>

      {/* Nome — visível apenas quando expandido */}
      {!compact && (
        <div className="min-w-0">
          <span className="block text-base font-bold leading-tight text-sidebar-foreground tracking-tight">
            FiscWise
          </span>
          <span className="block text-[10px] font-medium uppercase tracking-widest text-sidebar-muted">
            Gestão Contábil
          </span>
        </div>
      )}
    </div>
  );
}

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
      {/* Logo */}
      <div className="flex h-16 items-center justify-center border-b border-sidebar-border px-3 md:justify-start md:px-5">
        <FiscWiseLogo compact={false} />
        {/* Mobile: só ícone */}
        <div className="md:hidden">
          <FiscWiseLogo compact />
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 space-y-0.5 overflow-y-auto px-2 py-4">
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
        <div className="hidden items-center gap-2 rounded-lg px-3 py-2 md:flex">
          <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-sidebar-accent/20 text-xs font-semibold text-sidebar-accent">
            FW
          </div>
          <div className="min-w-0 flex-1">
            <p className="truncate text-xs font-medium text-sidebar-foreground">FiscWise</p>
            <p className="truncate text-[10px] text-sidebar-muted">fiscwise.com.br</p>
          </div>
        </div>
      </div>
    </aside>
  );
}
