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
  ChevronDown,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Logo } from '@/components/Logo';
import { useState } from 'react';

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
      { name: 'Foco de Hoje',  href: '/foco',      icon: Target, badge: '3', badgeVariant: 'danger' },
    ],
  },
  {
    label: 'Gestão',
    items: [
      { name: 'Clientes',          href: '/clientes',         icon: UsersRound },
      { name: 'Fechamento Mensal', href: '/fechamento',       icon: CalendarCheck2 },
      { name: 'Obrigações',        href: '/obrigacoes',       icon: ListChecks },
      { name: 'Documentos',        href: '/documentos',       icon: FolderKanban },
    ],
  },
  {
    label: 'Fiscal',
    items: [
      { name: 'Notas Fiscais',       href: '/notas-fiscais',      icon: FileText },
      { name: 'Central e-CAC',       href: '/ecac',               icon: ShieldCheck },
      { name: 'Guias e Pagamentos',  href: '/guias',              icon: Coins },
      { name: 'Caixa Postal Fiscal', href: '/caixa-postal-fiscal',icon: Mail, badge: '5', badgeVariant: 'warning' },
      { name: 'Procurações',         href: '/procuracoes',        icon: FileText },
      { name: 'Certificados',        href: '/certificados',       icon: Fingerprint },
    ],
  },
  {
    label: 'Financeiro & Canais',
    items: [
      { name: 'Financeiro',      href: '/financeiro', icon: ReceiptText },
      { name: 'WhatsApp',        href: '/whatsapp',   icon: MessageSquare },
      { name: 'Portal do Cliente', href: '/portal',   icon: Globe },
      { name: 'Relatórios',      href: '/relatorios', icon: BarChart3 },
    ],
  },
  {
    label: 'Sistema',
    collapsible: true,
    items: [
      { name: 'Aprender',       href: '/aprender',      icon: BookOpen },
      { name: 'Configurações',  href: '/configuracoes', icon: Settings },
    ],
  },
];

const BADGE_CLASSES = {
  danger:  'bg-destructive/90 text-white',
  warning: 'bg-warning/90 text-white',
  primary: 'bg-primary/90 text-primary-foreground',
};

export function Sidebar() {
  const location = useLocation();
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>({});

  const isActive = (href: string) =>
    location.pathname === href || location.pathname.startsWith(`${href}/`);

  const toggleGroup = (label: string) =>
    setCollapsed(prev => ({ ...prev, [label]: !prev[label] }));

  return (
    <aside
      className={cn(
        'flex h-full w-16 shrink-0 flex-col md:w-64',
        'bg-sidebar border-r border-sidebar-border',
        'transition-all duration-300 ease-in-out',
      )}
    >
      {/* Logo */}
      <Link
        to="/painel"
        aria-label="Ir para o painel"
        className="flex h-14 items-center justify-center border-b border-sidebar-border px-3 transition-opacity hover:opacity-80 md:justify-start md:px-5"
      >
        <div className="hidden md:block">
          <Logo variant="full" theme="dark" size={32} />
        </div>
        <div className="md:hidden">
          <Logo variant="icon" size={28} />
        </div>
      </Link>

      {/* Nav */}
      <nav className="flex-1 space-y-0 overflow-y-auto px-2 py-3 scrollbar-thin">
        {navGroups.map((group) => {
          const isCollapsed = collapsed[group.label];
          return (
            <div key={group.label} className="mb-1">
              {/* Group header */}
              <div className="mb-0.5 flex items-center justify-between px-2 pt-2">
                <p className="hidden truncate text-[9px] font-semibold uppercase tracking-[0.22em] text-sidebar-muted md:block">
                  {group.label}
                </p>
                {group.collapsible && (
                  <button
                    onClick={() => toggleGroup(group.label)}
                    className="hidden md:flex items-center text-sidebar-muted hover:text-sidebar-foreground transition-colors"
                    aria-label={isCollapsed ? 'Expandir' : 'Recolher'}
                  >
                    <ChevronDown
                      className={cn('h-3 w-3 transition-transform', isCollapsed && '-rotate-90')}
                    />
                  </button>
                )}
              </div>

              {/* Items */}
              {(!group.collapsible || !isCollapsed) &&
                group.items.map((item, i) => {
                  const active = isActive(item.href);
                  return (
                    <Link
                      key={item.name}
                      to={item.href}
                      aria-label={item.name}
                      title={item.name}
                      style={{ animationDelay: `${i * 30}ms` }}
                      className={cn(
                        'group relative flex items-center justify-center gap-3 rounded-lg px-2.5 py-2 text-sm font-medium',
                        'transition-all duration-150 md:justify-start',
                        active
                          ? [
                              'bg-sidebar-active-bg text-sidebar-active-fg shadow-sm',
                              'before:absolute before:left-0 before:top-1/2 before:h-4 before:w-[3px]',
                              'before:-translate-y-1/2 before:rounded-r-full before:bg-primary/70',
                            ]
                          : [
                              'text-sidebar-muted',
                              'hover:bg-sidebar-hover-bg hover:text-sidebar-foreground',
                            ],
                      )}
                    >
                      <item.icon
                        className={cn(
                          'h-[17px] w-[17px] shrink-0 transition-transform duration-150',
                          'group-hover:scale-110',
                          active ? 'text-sidebar-active-fg' : 'text-sidebar-muted',
                        )}
                      />
                      <span className="hidden flex-1 truncate md:inline">{item.name}</span>

                      {/* Badge */}
                      {item.badge && (
                        <span
                          className={cn(
                            'hidden md:flex h-4 min-w-[16px] items-center justify-center rounded-full px-1 text-[10px] font-bold',
                            BADGE_CLASSES[item.badgeVariant ?? 'primary'],
                          )}
                        >
                          {item.badge}
                        </span>
                      )}

                      {/* Tooltip mobile */}
                      <span className="pointer-events-none absolute left-full z-50 ml-2 hidden whitespace-nowrap rounded-md bg-popover px-2 py-1 text-xs text-popover-foreground shadow-token-sm group-hover:block md:hidden">
                        {item.name}
                        {item.badge && (
                          <span className={cn('ml-1.5 rounded-full px-1 text-[9px]', BADGE_CLASSES[item.badgeVariant ?? 'primary'])}>
                            {item.badge}
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
