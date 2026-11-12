import { Link, useLocation } from 'react-router-dom';
import {
  LayoutDashboard,
  Target,
  UsersRound,
  CalendarCheck2,
  FileText,
  ShieldCheck,
  Coins,
  ListChecks,
  FolderKanban,
  Mail,
  Fingerprint,
  ReceiptText,
  MessageSquare,
  Globe,
  BarChart3,
  BookOpen,
  Settings,
  RefreshCw,
  ChevronDown,
  GraduationCap,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Logo } from '@/components/Logo';
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { fetchFocusItems } from '@/features/focus/api';

type NavItem = {
  name: string;
  href: string;
  icon: React.ElementType;
  badge?: string;
  badgeVariant?: 'danger' | 'warning' | 'primary';
};

type NavGroup = {
  label: string;
  items: NavItem[];
  collapsible?: boolean;
};

const navGroups: NavGroup[] = [
  {
    label: 'Operação diária',
    items: [
      { name: 'Painel',        href: '/painel',    icon: LayoutDashboard },
      { name: 'Foco de hoje',  href: '/foco',      icon: Target },
    ],
  },
  {
    label: 'Gestão',
    items: [
      { name: 'Clientes',          href: '/clientes',         icon: UsersRound },
      { name: 'Fechamento mensal', href: '/fechamento',       icon: CalendarCheck2 },
      { name: 'Obrigações',        href: '/obrigacoes',       icon: ListChecks },
      { name: 'Documentos',        href: '/documentos',       icon: FolderKanban },
    ],
  },
  {
    label: 'Fiscal',
    items: [
      { name: 'Notas fiscais',       href: '/notas-fiscais',      icon: FileText },
      { name: 'Central e-CAC',       href: '/ecac',               icon: ShieldCheck },
      { name: 'Guias e pagamentos',  href: '/guias',              icon: Coins },
      { name: 'Caixa postal fiscal', href: '/caixa-postal-fiscal',icon: Mail },
      { name: 'Procurações',         href: '/procuracoes',        icon: FileText },
      { name: 'Certificados',        href: '/certificados',       icon: Fingerprint },
    ],
  },
  {
    label: 'Financeiro & Canais',
    items: [
      { name: 'Financeiro',      href: '/financeiro', icon: ReceiptText },
      { name: 'WhatsApp',        href: '/whatsapp',   icon: MessageSquare },
      { name: 'Portal do cliente', href: '/portal',   icon: Globe },
      { name: 'Relatórios',      href: '/relatorios', icon: BarChart3 },
    ],
  },
  {
    label: 'Sistema',
    collapsible: true,
    items: [
      { name: 'Minicurso',      href: '/minicurso',     icon: GraduationCap },
      { name: 'Aprender',       href: '/aprender',      icon: BookOpen },
      { name: 'Configurações',  href: '/configuracoes', icon: Settings },
      { name: 'Sincronização',  href: '/sincronizacao', icon: RefreshCw },
    ],
  },
];

const BADGE_CLASSES = {
  danger:  'bg-destructive text-destructive-foreground',
  warning: 'bg-warning text-warning-foreground',
  primary: 'bg-primary text-primary-foreground',
};

export function Sidebar() {
  const location = useLocation();
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>({});

  // Badge real do "Foco de Hoje": itens urgentes (críticos + de hoje).
  const { data: focusItems } = useQuery({
    queryKey: ['focus-items'],
    queryFn: fetchFocusItems,
    staleTime: 60_000,
    retry: false,
  });
  const focusCount = (focusItems ?? []).filter(
    (i) => i.group === 'critical' || i.group === 'today'
  ).length;

  const isActive = (href: string) =>
    location.pathname === href || location.pathname.startsWith(`${href}/`);

  const toggleGroup = (label: string) =>
    setCollapsed(prev => ({ ...prev, [label]: !prev[label] }));

  return (
    <aside
      className={cn(
        'flex h-full w-16 shrink-0 flex-col md:w-60',
        'border-r border-sidebar-border bg-sidebar',
      )}
    >
      {/* Logo */}
      <Link
        to="/painel"
        aria-label="Ir para o painel"
        className="flex h-14 shrink-0 items-center justify-center border-b border-sidebar-border px-3 transition-opacity duration-150 hover:opacity-90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-primary md:justify-start md:px-4"
      >
        <div className="hidden md:block">
          <Logo variant="full" theme="dark" size={28} />
        </div>
        <div className="md:hidden">
          <Logo variant="icon" size={28} />
        </div>
      </Link>

      {/* Nav */}
      <nav aria-label="Navegação principal" className="flex-1 overflow-y-auto px-2 py-3">
        {navGroups.map((group) => {
          const isCollapsed = collapsed[group.label];
          return (
            <div key={group.label} className="mb-2 last:mb-0">
              {/* Group header */}
              <div className="mb-1 hidden h-6 items-center justify-between px-2.5 md:flex">
                <p className="truncate text-[11px] font-medium text-sidebar-muted">
                  {group.label}
                </p>
                {group.collapsible && (
                  <button
                    onClick={() => toggleGroup(group.label)}
                    className="flex h-6 w-6 items-center justify-center rounded-sm text-sidebar-muted transition-colors duration-150 hover:text-sidebar-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
                    aria-label={isCollapsed ? `Expandir ${group.label}` : `Recolher ${group.label}`}
                    aria-expanded={!isCollapsed}
                  >
                    <ChevronDown
                      className={cn('h-3.5 w-3.5 transition-transform duration-150', isCollapsed && '-rotate-90')}
                    />
                  </button>
                )}
              </div>

              {/* Items */}
              {(!group.collapsible || !isCollapsed) &&
                group.items.map((item) => {
                  const active = isActive(item.href);
                  const badge =
                    item.href === '/foco' && focusCount > 0
                      ? String(focusCount)
                      : item.badge;
                  const badgeVariant =
                    item.href === '/foco' ? 'danger' : item.badgeVariant;
                  return (
                    <Link
                      key={item.name}
                      to={item.href}
                      aria-label={item.name}
                      data-tour={`nav-${item.href}`}
                      aria-current={active ? 'page' : undefined}
                      title={item.name}
                      className={cn(
                        'group relative flex h-10 items-center justify-center gap-3 rounded-md px-2.5 text-sm font-medium md:h-9 md:justify-start',
                        'transition-colors duration-150 ease-out',
                        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:ring-offset-sidebar',
                        active
                          ? 'bg-sidebar-active-bg text-sidebar-active-fg'
                          : 'text-sidebar-muted hover:bg-sidebar-hover-bg hover:text-sidebar-foreground',
                      )}
                    >
                      <item.icon
                        aria-hidden="true"
                        className={cn(
                          'h-[18px] w-[18px] shrink-0',
                          active ? 'text-sidebar-active-fg' : 'text-sidebar-muted group-hover:text-sidebar-foreground',
                        )}
                      />
                      <span className="hidden flex-1 truncate md:inline">{item.name}</span>

                      {/* Badge */}
                      {badge && (
                        <span
                          className={cn(
                            'hidden h-5 min-w-[20px] items-center justify-center rounded-full px-1.5 text-[11px] font-semibold tabular-nums md:flex',
                            active && 'bg-white/20 text-white',
                            BADGE_CLASSES[badgeVariant ?? 'primary'],
                          )}
                        >
                          {badge}
                        </span>
                      )}

                      {/* Tooltip mobile */}
                      <span className="pointer-events-none absolute left-full z-50 ml-2 hidden whitespace-nowrap rounded-md border border-border bg-popover px-2 py-1 text-xs text-popover-foreground shadow-md group-hover:block group-focus-visible:block md:hidden">
                        {item.name}
                        {badge && (
                          <span className={cn('ml-1.5 rounded-full px-1 text-[11px] tabular-nums', BADGE_CLASSES[badgeVariant ?? 'primary'])}>
                            {badge}
                          </span>
                        )}
                      </span>
                    </Link>
                  );
                })}
            </div>
          );
        })}
      </nav>
    </aside>
  );
}
