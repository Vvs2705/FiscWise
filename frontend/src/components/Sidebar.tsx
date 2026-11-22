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
  Settings,
  RefreshCw,
  ChevronDown,
  Wallet,
  GraduationCap,
  CreditCard,
  Scale,
  Library,
  ClipboardCheck,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Logo } from '@/components/Logo';
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { fetchFocusItems } from '@/features/focus/api';
import { useSubscriptionUsage, useTenantInfo } from '@/lib/hooks/useSubscription';
import { PLAN_ROUTE_FEATURES, planLacksFeature } from '@/features/subscription/planFeatures';
import { useAuthStore } from '@/stores/authStore';
import { useEquipeFiscwise } from '@/lib/hooks/useAjustesFiscais';

type NavItem = {
  name: string;
  href: string;
  icon: React.ElementType;
  badge?: string;
  badgeVariant?: 'danger' | 'warning' | 'primary';
  /** Uso menos frequente: fica recolhido atrás de "Mais" (sempre visível no menu de ícones). */
  rare?: boolean;
};

type NavGroup = {
  label: string;
  items: NavItem[];
};

/*
 * Menu por tarefa (6 grupos). Nenhuma rota foi removida: só agrupamento,
 * ordem e rótulo. Itens `rare` ficam recolhidos em "Mais"; o grupo abre sozinho
 * quando a rota ativa está entre eles.
 */
const navGroups: NavGroup[] = [
  {
    label: 'Hoje',
    items: [
      { name: 'Painel',        href: '/painel',    icon: LayoutDashboard },
      { name: 'Foco de hoje',  href: '/foco',      icon: Target },
    ],
  },
  {
    label: 'Clientes',
    items: [
      { name: 'Clientes',          href: '/clientes',     icon: UsersRound },
      { name: 'Documentos',        href: '/documentos',   icon: FolderKanban },
      { name: 'Portal do cliente', href: '/portal',       icon: Globe },
      { name: 'Certificados',      href: '/certificados', icon: Fingerprint },
      { name: 'Procurações',       href: '/procuracoes',  icon: FileText, rare: true },
      { name: 'WhatsApp',          href: '/whatsapp',     icon: MessageSquare, rare: true },
    ],
  },
  {
    label: 'Notas e obrigações',
    items: [
      { name: 'Obrigações',          href: '/obrigacoes',       icon: ListChecks },
      { name: 'Fechamento mensal',   href: '/fechamento',       icon: CalendarCheck2 },
      { name: 'Notas fiscais',       href: '/notas-fiscais',    icon: ReceiptText },
      { name: 'Guias e pagamentos',  href: '/guias',            icon: Coins },
      { name: 'Central e-CAC',       href: '/ecac',             icon: ShieldCheck, rare: true },
      { name: 'Caixa postal fiscal', href: '/caixa-postal-fiscal', icon: Mail, rare: true },
      { name: 'Ajustes fiscais',     href: '/ajustes-fiscais',  icon: Scale, rare: true },
    ],
  },
  {
    label: 'Financeiro',
    items: [
      { name: 'Financeiro', href: '/financeiro', icon: Wallet },
      { name: 'Relatórios', href: '/relatorios', icon: BarChart3 },
    ],
  },
  {
    label: 'Aprender',
    items: [
      { name: 'Minicurso',            href: '/minicurso',                           icon: GraduationCap },
      { name: 'Base de conhecimento', href: '/configuracoes?aba=base_conhecimento', icon: Library },
    ],
  },
  {
    label: 'Conta e sistema',
    items: [
      { name: 'Configurações',      href: '/configuracoes', icon: Settings },
      { name: 'Plano e assinatura', href: '/assinatura',    icon: CreditCard },
      { name: 'Sincronização',      href: '/sincronizacao', icon: RefreshCw, rare: true },
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
  // Escolha manual de abrir/fechar "Mais" por grupo; sem escolha, abre só se a rota ativa estiver lá.
  const [moreOpen, setMoreOpen] = useState<Record<string, boolean>>({});

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

  // Recurso fora do plano: o item continua (dá para consultar), marcado "Plano".
  // Conta vencida fica de fora: a faixa do teste já explica o "só leitura".
  const role = useAuthStore((s) => s.user?.role);
  const isOffice = !!role && role !== 'client';
  const { data: usage } = useSubscriptionUsage();
  const { data: tenant } = useTenantInfo(isOffice);
  const outOfPlan = (href: string) => {
    const feature = PLAN_ROUTE_FEATURES[href];
    return !!feature && isOffice && !tenant?.acesso_expirado && planLacksFeature(usage?.features, feature);
  };

  const isActive = (href: string) => {
    const [path, query] = href.split('?');
    if (query) return location.pathname === path && location.search.includes(query);
    if (path === '/configuracoes' && location.search.includes('aba=base_conhecimento')) return false;
    return location.pathname === path || location.pathname.startsWith(`${path}/`);
  };

  // Fila de análise dos ajustes fiscais: só para a equipe FiscWise.
  const { data: equipeFiscwise } = useEquipeFiscwise(isOffice);
  const grupos: NavGroup[] = equipeFiscwise
    ? navGroups.map((g) =>
        g.label === 'Conta e sistema'
          ? {
              ...g,
              items: [
                ...g.items,
                { name: 'Equipe: ajustes fiscais', href: '/equipe/ajustes-fiscais', icon: ClipboardCheck },
              ],
            }
          : g,
      )
    : navGroups;

  const toggleMore = (label: string, current: boolean) =>
    setMoreOpen((prev) => ({ ...prev, [label]: !current }));

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
        {grupos.map((group) => {
          const main = group.items.filter((i) => !i.rare);
          const more = group.items.filter((i) => i.rare);
          const hasActiveMore = more.some((i) => isActive(i.href));
          const open = moreOpen[group.label] ?? hasActiveMore;
          const moreId = `nav-more-${group.label.replace(/\s+/g, '-').toLowerCase()}`;

          const renderItem = (item: NavItem) => {
            const active = isActive(item.href);
            const lockedByPlan = outOfPlan(item.href);
            const badge =
              item.href === '/foco' && focusCount > 0
                ? String(focusCount)
                : lockedByPlan
                  ? 'Plano'
                  : item.badge;
            const badgeVariant =
              item.href === '/foco' ? 'danger' : lockedByPlan ? 'warning' : item.badgeVariant;
            return (
              <Link
                key={item.href}
                to={item.href}
                aria-label={item.name}
                data-tour={`nav-${item.href}`}
                aria-current={active ? 'page' : undefined}
                title={lockedByPlan ? `${item.name} (fora do seu plano)` : item.name}
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
          };

          return (
            <div key={group.label} role="group" aria-label={group.label} className="mb-3 last:mb-0">
              {/* Rótulo do grupo (só com o menu largo; no menu de ícones vira um filete) */}
              <p className="mb-1 hidden h-6 items-center truncate px-2.5 text-[11px] font-medium text-sidebar-muted md:flex">
                {group.label}
              </p>
              <div aria-hidden="true" className="mx-2 mb-2 h-px bg-sidebar-border md:hidden" />

              {main.map(renderItem)}

              {more.length > 0 && (
                <>
                  <button
                    type="button"
                    onClick={() => toggleMore(group.label, open)}
                    aria-expanded={open}
                    aria-controls={moreId}
                    className="hidden h-8 w-full items-center gap-3 rounded-md px-2.5 text-xs font-medium text-sidebar-muted transition-colors duration-150 hover:bg-sidebar-hover-bg hover:text-sidebar-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary md:flex"
                  >
                    <ChevronDown
                      aria-hidden="true"
                      className={cn('h-[18px] w-[18px] shrink-0 transition-transform duration-150', !open && '-rotate-90')}
                    />
                    <span className="flex-1 truncate text-left">{open ? 'Menos' : `Mais ${more.length}`}</span>
                  </button>
                  {/* Menu de ícones (< md): sem recolher, para nenhuma rota ficar inacessível. */}
                  <div id={moreId} className={cn(!open && 'hidden max-md:block')}>
                    {more.map(renderItem)}
                  </div>
                </>
              )}
            </div>
          );
        })}
      </nav>
    </aside>
  );
}
