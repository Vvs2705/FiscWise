import { useMemo, useState } from 'react';
import { motion } from 'framer-motion';
import { dateBR, moneyBRL, useDashboardOverview, useProductivityOverview } from '@/lib/hooks/useOperations';
import { DashboardHero } from '@/features/dashboard/components/DashboardHero';
import { DailyFocusCard } from '@/features/dashboard/components/DailyFocusCard';
import { MetricsGrid } from '@/features/dashboard/components/MetricsGrid';
import { ClientAttentionList } from '@/features/dashboard/components/ClientAttentionList';
import { FiscalWeekTimeline } from '@/features/dashboard/components/FiscalWeekTimeline';
import { PendingDocumentsCard } from '@/features/dashboard/components/PendingDocumentsCard';
import { MonthlyClosingCard } from '@/features/dashboard/components/MonthlyClosingCard';
import { PortfolioRiskCard } from '@/features/dashboard/components/PortfolioRiskCard';
import { ModoFocoModal } from '@/features/dashboard/components/ModoFocoModal';
import { staggerContainer, fadeIn } from '@/lib/motion';

function startOfToday() {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  return today;
}

function parseDate(value: string) {
  const parsed = new Date(value);
  parsed.setHours(0, 0, 0, 0);
  return parsed;
}

function daysUntil(value: string) {
  const diff = parseDate(value).getTime() - startOfToday().getTime();
  return Math.round(diff / 86_400_000);
}

export function DashboardPage() {
  const [isModoFocoOpen, setIsModoFocoOpen] = useState(false);
  const { data, isLoading, isError } = useDashboardOverview();
  const { data: prod } = useProductivityOverview();

  const upcomingDeadlines = useMemo(
    () => data?.upcoming_deadlines ?? [],
    [data?.upcoming_deadlines]
  );
  const recentReceivables = useMemo(
    () => data?.recent_receivables ?? [],
    [data?.recent_receivables]
  );

  const todaysDeadlines = useMemo(
    () => upcomingDeadlines.filter((item) => daysUntil(item.due_date) === 0),
    [upcomingDeadlines]
  );

  // Focus Items for DailyFocusCard
  const focusItems = useMemo(() => {
    const items = [
      {
        id: 'deadlines-today',
        label: 'obrigações vencem hoje',
        value: todaysDeadlines.length,
        tone: todaysDeadlines.length > 0 ? ('danger' as const) : ('success' as const),
      },
      {
        id: 'deadlines-overdue',
        label: 'obrigações em atraso',
        value: data?.overdue_deadlines ?? 0,
        tone: (data?.overdue_deadlines ?? 0) > 0 ? ('danger' as const) : ('success' as const),
      },
      {
        id: 'docs-review',
        label: 'documentos aguardando conferência',
        value: prod?.docs_awaiting_approval ?? 0,
        tone: (prod?.docs_awaiting_approval ?? 0) > 0 ? ('warning' as const) : ('success' as const),
      },
      {
        id: 'certificates',
        label: 'certificados vencendo em 30 dias',
        value: data?.certificates_expiring_30d ?? prod?.certificates_expiring_30d ?? 0,
        tone:
          (data?.certificates_expiring_30d ?? prod?.certificates_expiring_30d ?? 0) > 0
            ? ('warning' as const)
            : ('info' as const),
      },
    ];

    return items.filter((item) => item.value > 0).slice(0, 3);
  }, [data?.certificates_expiring_30d, data?.overdue_deadlines, prod?.certificates_expiring_30d, prod?.docs_awaiting_approval, todaysDeadlines.length]);

  const totalFocusCount = focusItems.reduce((sum, item) => sum + item.value, 0);

  // Metrics for MetricsGrid
  const metrics = useMemo(
    () => [
      {
        id: 'obligations',
        label: 'Obrigações em aberto',
        value: data?.pending_deadlines ?? 0,
        detail: `${data?.overdue_deadlines ?? 0} atrasadas`,
        icon: 'calendar' as const,
      },
      {
        id: 'clients',
        label: 'Clientes ativos',
        value: data?.active_clients ?? 0,
        detail: 'carteira atual',
        icon: 'users' as const,
      },
      {
        id: 'documents',
        label: 'Documentos pendentes',
        value: prod?.docs_awaiting_approval ?? 0,
        detail: 'aguardando conferência',
        icon: 'document' as const,
      },
      {
        id: 'receivables',
        label: 'Recebíveis em atraso',
        value: data?.overdue_receivables ?? 0,
        detail: moneyBRL(data?.receivables_amount_overdue ?? 0),
        icon: 'receipt' as const,
      },
    ],
    [data, prod]
  );

  // Clients needing attention for ClientAttentionList
  const attentionClients = useMemo(() => {
    const fromPending =
      prod?.clients_with_most_pending.map((client) => ({
        id: `pending-${client.client_id}`,
        name: client.client_name,
        reason:
          client.pending_count === 1
            ? '1 pendência operacional aberta'
            : `${client.pending_count} pendências operacionais abertas`,
        risk: (client.pending_count >= 3 ? 'Alto' : 'Médio') as 'Alto' | 'Médio',
        icon: 'alert' as const,
      })) ?? [];

    const fromOverdueReceivables = recentReceivables
      .filter((item) => item.status === 'overdue')
      .map((item) => ({
        id: `receivable-${item.id}`,
        name: item.client_name,
        reason: `Recebível em atraso de ${moneyBRL(item.amount)}`,
        risk: 'Médio' as const,
        icon: 'clock' as const,
      }));

    const allClients = [...fromPending, ...fromOverdueReceivables];
    const unique = new Map<string, (typeof allClients)[0]>();

    allClients.forEach((item) => {
      if (!unique.has(item.name)) {
        unique.set(item.name, item);
      }
    });

    return Array.from(unique.values()).slice(0, 5);
  }, [prod?.clients_with_most_pending, recentReceivables]);

  // Timeline for FiscalWeekTimeline
  const weekTimeline = useMemo(() => {
    const days = ['Hoje', 'Amanhã', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo'];
    const today = new Date();

    return days.slice(0, 5).map((day, index) => {
      const date = new Date(today);
      date.setDate(today.getDate() + index);

      const dayDeadlines = upcomingDeadlines
        .filter((deadline) => {
          const deadlineDate = parseDate(deadline.due_date);
          return deadlineDate.toDateString() === date.toDateString();
        })
        .map((deadline) => ({
          id: deadline.id,
          title: deadline.title,
          type: 'obligation' as const,
          status: deadline.status === 'completed' ? ('completed' as const) : ('pending' as const),
          time: undefined,
        }));

      return {
        day,
        date: dateBR(date.toISOString()),
        isToday: index === 0,
        items: dayDeadlines,
      };
    });
  }, [upcomingDeadlines]);

  // Documents for PendingDocumentsCard
  const pendingDocuments = useMemo(() => {
    // Mock data - replace with real data when available
    return [];
  }, []);

  // Monthly closing stats for MonthlyClosingCard
  const closingStats = useMemo(() => {
    const total = (prod?.total_delivered ?? 0) + (prod?.total_pending ?? 0) + (prod?.total_in_progress ?? 0) + (prod?.total_overdue ?? 0);
    const completed = prod?.total_delivered ?? 0;
    const completionPercentage = total > 0 ? Math.round((completed / total) * 100) : 0;

    return {
      completed: prod?.total_delivered ?? 0,
      inProgress: prod?.total_in_progress ?? 0,
      blockedByClient: 0, // Not available in current data
      overdue: prod?.total_overdue ?? 0,
      total,
      completionPercentage,
    };
  }, [prod]);

  // Portfolio risk for PortfolioRiskCard
  const portfolioRisk = useMemo(() => {
    let score = 100;

    // Deduct points for issues
    const overdueDeadlines = data?.overdue_deadlines ?? 0;
    const pendingDocs = prod?.docs_awaiting_approval ?? 0;
    const expiringCerts = data?.certificates_expiring_30d ?? 0;
    const overdueReceivables = data?.overdue_receivables ?? 0;

    score -= overdueDeadlines * 5;
    score -= pendingDocs * 2;
    score -= expiringCerts * 3;
    score -= overdueReceivables * 4;

    score = Math.max(0, Math.min(100, score));

    const factors = [];
    if (overdueDeadlines > 0) {
      factors.push({
        label: 'Obrigações atrasadas',
        impact: -overdueDeadlines * 5,
        status: 'critical' as const,
      });
    }
    if (pendingDocs > 0) {
      factors.push({
        label: 'Documentos pendentes',
        impact: -pendingDocs * 2,
        status: 'warning' as const,
      });
    }
    if (expiringCerts > 0) {
      factors.push({
        label: 'Certificados vencendo',
        impact: -expiringCerts * 3,
        status: 'warning' as const,
      });
    }
    if (overdueReceivables > 0) {
      factors.push({
        label: 'Recebíveis em atraso',
        impact: -overdueReceivables * 4,
        status: 'critical' as const,
      });
    }

    return { score, factors };
  }, [data, prod]);

  const currentMonth = new Date().toLocaleDateString('pt-BR', { month: 'long' });
  const currentYear = new Date().getFullYear();

  return (
    <div
      className="min-h-full rounded-[32px] border border-fw-border bg-fw-bg text-fw-text"
      style={{
        backgroundImage:
          'radial-gradient(circle at 20% 20%, rgba(45, 212, 191, 0.12), transparent 28%), radial-gradient(circle at 80% 30%, rgba(56, 189, 248, 0.08), transparent 30%)',
      }}
    >
      <motion.div
        variants={staggerContainer}
        initial="initial"
        animate="animate"
        className="mx-auto max-w-[1400px] space-y-6 p-5 md:p-8"
      >
        {/* Hero Section */}
        <motion.div variants={fadeIn}>
          <DashboardHero isError={isError} onStartFocusMode={() => setIsModoFocoOpen(true)} />
        </motion.div>

        {/* Daily Focus + Metrics Grid */}
        <div className="grid gap-6 lg:grid-cols-[1fr_2fr]">
          <motion.div variants={fadeIn} id="tour-focus">
            <DailyFocusCard
              focusItems={focusItems}
              totalCount={totalFocusCount}
              isLoading={isLoading}
              onStartFocusMode={() => setIsModoFocoOpen(true)}
            />
          </motion.div>

          <motion.div variants={fadeIn}>
            <MetricsGrid metrics={metrics} />
          </motion.div>
        </div>

        {/* Main Content Grid */}
        <div className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
          {/* Left Column */}
          <motion.div variants={staggerContainer} className="space-y-6">
            <motion.div variants={fadeIn} id="tour-attention">
              <ClientAttentionList clients={attentionClients} isLoading={isLoading} />
            </motion.div>

            <motion.div variants={fadeIn} id="tour-deadlines">
              <FiscalWeekTimeline timeline={weekTimeline} isLoading={isLoading} />
            </motion.div>
          </motion.div>

          {/* Right Column */}
          <motion.div variants={staggerContainer} className="space-y-6">
            <motion.div variants={fadeIn}>
              <PendingDocumentsCard
                documents={pendingDocuments}
                totalPending={prod?.docs_awaiting_approval ?? 0}
                isLoading={isLoading}
              />
            </motion.div>

            <motion.div variants={fadeIn}>
              <MonthlyClosingCard
                month={currentMonth}
                year={currentYear}
                stats={closingStats}
                isLoading={isLoading}
              />
            </motion.div>

            <motion.div variants={fadeIn} id="tour-risk">
              <PortfolioRiskCard
                score={portfolioRisk.score}
                factors={portfolioRisk.factors}
                isLoading={isLoading}
                onStartFocusMode={() => setIsModoFocoOpen(true)}
              />
            </motion.div>
          </motion.div>
        </div>
      </motion.div>

      <ModoFocoModal
        isOpen={isModoFocoOpen}
        onClose={() => setIsModoFocoOpen(false)}
        beforeScore={portfolioRisk.score}
      />
    </div>
  );
}
