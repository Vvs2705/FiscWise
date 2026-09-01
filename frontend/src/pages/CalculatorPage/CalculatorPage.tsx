import { useState } from 'react';
import { Calculator, MessageSquare, History, TrendingDown, Zap } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { PlanBadge } from './PlanBadge';
import { SimulatorTab } from './SimulatorTab';
import { ChatTab } from './ChatTab';
import { HistoryTab } from './HistoryTab';
import { BenefitsTab } from './BenefitsTab';
import { useAuthStore } from '@/stores/authStore';
import { fetchTenant } from '@/lib/auth';
import { useQuery } from '@tanstack/react-query';
import { cn } from '@/lib/utils';
import type { SubscriptionPlan } from '@/lib/hooks/useCalculator';
import { PLAN_INFO, planHasChat, planHasBenefits } from '@/lib/hooks/useCalculator';

type TabId = 'simulator' | 'chat' | 'history' | 'benefits';

const TABS: {
  id: TabId;
  label: string;
  icon: React.ElementType;
  requiredPlan?: Exclude<SubscriptionPlan, 'free'>;
}[] = [
  { id: 'simulator', label: 'Simulador', icon: Calculator },
  { id: 'chat', label: 'Chat', icon: MessageSquare, requiredPlan: 'intermediario' },
  { id: 'history', label: 'Histórico', icon: History },
  { id: 'benefits', label: 'Benefícios', icon: TrendingDown, requiredPlan: 'premium' },
];

// ─── Plan info card ──────────────────────────────────────────────────────────

function PlanCard({ plan }: { plan: SubscriptionPlan }) {
  const info = PLAN_INFO[plan];
  const nextPlan: SubscriptionPlan | null =
    plan === 'free' ? 'intermediario' : plan === 'intermediario' ? 'premium' : null;

  return (
    <Card className="mb-6">
      <CardContent className="flex flex-wrap items-center justify-between gap-4 py-4">
        <div className="flex items-center gap-3">
          <div className="flex flex-col gap-1">
            <div className="flex items-center gap-2">
              <p className="text-sm font-semibold">Seu plano atual</p>
              <PlanBadge plan={plan} />
            </div>
            <p className="text-xs text-muted-foreground">
              {info.features.slice(0, 2).join(' · ')}
              {info.features.length > 2 && ' · ...'}
            </p>
          </div>
        </div>

        {nextPlan && (
          <Button
            size="sm"
            onClick={() => (window.location.href = '/financeiro')}
            aria-label={`Fazer upgrade para o plano ${PLAN_INFO[nextPlan].label}`}
          >
            <Zap className="h-3.5 w-3.5" aria-hidden="true" />
            Upgrade para {PLAN_INFO[nextPlan].label}
          </Button>
        )}
      </CardContent>
    </Card>
  );
}

// ─── Main page ───────────────────────────────────────────────────────────────

export function CalculatorPage() {
  const [activeTab, setActiveTab] = useState<TabId>('simulator');
  const { user } = useAuthStore();

  const { data: tenant } = useQuery({
    queryKey: ['tenant'],
    queryFn: fetchTenant,
    // Only run if user is authenticated
    enabled: !!user,
    staleTime: 5 * 60 * 1000,
  });

  // Normalise plan slug from backend to our union type
  function normalisePlan(slug: string | undefined | null): SubscriptionPlan {
    if (slug === 'intermediario' || slug === 'premium') return slug;
    return 'free';
  }

  const plan = normalisePlan(tenant?.plan_slug);

  const visibleTabs = TABS.filter((tab) => {
    // Always show all tabs — lock state is handled inside each tab
    return true;
  });

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Calculadora Fiscal</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Simule regimes tributários, calcule ICMS e PIS/COFINS com apoio de inteligência artificial.
        </p>
      </div>

      {/* Plan card */}
      <PlanCard plan={plan} />

      {/* Tabs */}
      <div
        role="tablist"
        aria-label="Seções da calculadora fiscal"
        className="flex gap-1 rounded-xl border border-border bg-muted/30 p-1"
      >
        {visibleTabs.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          const isLocked =
            (tab.id === 'chat' && !planHasChat(plan)) ||
            (tab.id === 'benefits' && !planHasBenefits(plan));

          return (
            <button
              key={tab.id}
              role="tab"
              aria-selected={isActive}
              aria-controls={`tabpanel-${tab.id}`}
              id={`tab-${tab.id}`}
              onClick={() => setActiveTab(tab.id)}
              className={cn(
                'relative flex flex-1 items-center justify-center gap-1.5 rounded-lg px-2 py-2 text-sm font-medium',
                'transition-all duration-150 ease-spring',
                'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1 focus-visible:ring-offset-background',
                isActive
                  ? 'bg-background text-foreground shadow-sm'
                  : 'text-muted-foreground hover:text-foreground',
              )}
            >
              <Icon
                className={cn(
                  'h-4 w-4 shrink-0',
                  isLocked && !isActive ? 'opacity-50' : '',
                )}
                aria-hidden="true"
              />
              <span className="hidden sm:inline">{tab.label}</span>
              {isLocked && (
                <span
                  className="absolute right-1 top-1 h-1.5 w-1.5 rounded-full bg-muted-foreground/60"
                  aria-label="Recurso bloqueado — requer upgrade"
                />
              )}
            </button>
          );
        })}
      </div>

      {/* Tab panels */}
      <div
        id={`tabpanel-simulator`}
        role="tabpanel"
        aria-labelledby={`tab-simulator`}
        hidden={activeTab !== 'simulator'}
      >
        {activeTab === 'simulator' && <SimulatorTab plan={plan} />}
      </div>

      <div
        id={`tabpanel-chat`}
        role="tabpanel"
        aria-labelledby={`tab-chat`}
        hidden={activeTab !== 'chat'}
      >
        {activeTab === 'chat' && <ChatTab plan={plan} />}
      </div>

      <div
        id={`tabpanel-history`}
        role="tabpanel"
        aria-labelledby={`tab-history`}
        hidden={activeTab !== 'history'}
      >
        {activeTab === 'history' && <HistoryTab plan={plan} />}
      </div>

      <div
        id={`tabpanel-benefits`}
        role="tabpanel"
        aria-labelledby={`tab-benefits`}
        hidden={activeTab !== 'benefits'}
      >
        {activeTab === 'benefits' && <BenefitsTab plan={plan} />}
      </div>
    </div>
  );
}
