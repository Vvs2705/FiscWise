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
import { Logo } from '@/components/Logo';

const navigation = [
  { name: 'Dashboard',      href: '/dashboard',      icon: LayoutDashboard },
  { name: 'Clientes',       href: '/clientes',        icon: UsersRound },
  { name: 'Documentos',     href: '/documentos',      icon: FolderKanban },
  { name: 'Agenda / Prazos',href: '/agenda-prazos',   icon: CalendarClock },
  { name: 'Certificados',   href: '/certificados',    icon: ShieldCheck },
  { name: 'Financeiro',     href: '/financeiro',      icon: ReceiptText },
  { name: 'Configurações',  href: '/configuracoes',   icon: Settings },
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
      {/* Logo */}
      <div className="flex h-16 items-center justify-center border-b border-sidebar-border px-3 md:justify-start md:px-5">
        {/* Desktop: logo completo */}
        <div className="hidden md:block">
          <Logo variant="full" theme="dark" size={34} />
        </div>
        {/* Mobile: só ícone */}
        <div className="md:hidden">
          <Logo variant="icon" size={32} />
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
