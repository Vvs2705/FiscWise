import { type ReactNode, useMemo } from 'react';
import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import {
  AlertTriangle,
  ArrowRight,
  CalendarClock,
  CheckCircle2,
  Clock3,
  FileCheck2,
  ReceiptText,
  ShieldAlert,
  Users2,
  UsersRound,
} from 'lucide-react';
import { dateBR, moneyBRL, useDashboardOverview, useProductivityOverview } from '@/lib/hooks/useOperations';
import { usePermission } from '@/lib/hooks/usePermission';

const containerVariants = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.08 },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 18 },
  show: { opacity: 1, y: 0, transition: { duration: 0.45, ease: 'easeOut' as const } },
};

type AttentionLevel = 'alto' | 'medio' | 'regular';

interface AttentionItem {
  id: string;
  clientName: string;
  reason: string;
  level: AttentionLevel;
  actionLabel: string;
  actionPath: string;
}

interface FocusItem {
  id: string;
  label: string;
  value: number;
  tone: 'danger' | 'warning' | 'info' | 'success';
}

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

function badgeClasses(level: AttentionLevel) {
  if (level === 'alto') {
    return 'border-red-400/30 bg-red-500/10 text-red-200';
  }

  if (level === 'medio') {
    return 'border-amber-400/30 bg-amber-500/10 text-amber-100';
  }

  return 'border-slate-400/30 bg-white/5 text-slate-200';
}

function toneClasses(tone: FocusItem['tone']) {
  if (tone === 'danger') {
    return 'border-red-400/30 bg-red-500/10 text-red-100';
  }

  if (tone === 'warning') {
    return 'border-amber-400/30 bg-amber-500/10 text-amber-100';
  }

  if (tone === 'success') {
    return 'border-emerald-400/30 bg-emerald-500/10 text-emerald-100';
  }

  return 'border-cyan-400/30 bg-cyan-500/10 text-cyan-100';
}

function formatDueLabel(days: number) {
  if (days <= 0) return 'Hoje';
  if (days === 1) return 'Amanhã';
  return `Em ${days} dias`;
}

function SectionCard({
  children,
  className = '',
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <motion.section
      variants={itemVariants}
      className={`rounded-[28px] border border-white/10 bg-[#111926] shadow-[0_20px_60px_rgba(0,0,0,0.28)] ${className}`}
    >
      {children}
    </motion.section>
  );
}

function SectionHeader({
  eyebrow,
  title,
  description,
}: {
  eyebrow: string;
  title: string;
  description: string;
}) {
  return (
    <div className="mb-6">
      <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-[#7dd3fc]">
        {eyebrow}
      </p>
      <h2 className="mt-2 text-2xl font-semibold tracking-tight text-white">{title}</h2>
      <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-300">{description}</p>
    </div>
  );
}

export function DashboardPage() {
  const navigate = useNavigate();
  const { hasRole } = usePermission();
  const isAdmin = hasRole('admin');
  const { data, isLoading, isError } = useDashboardOverview();
  const { data: prod } = useProductivityOverview();

  const upcomingDeadlines = data?.upcoming_deadlines ?? [];
  const recentReceivables = data?.recent_receivables ?? [];

  const todaysDeadlines = useMemo(
    () => upcomingDeadlines.filter((item) => daysUntil(item.due_date) === 0),
    [upcomingDeadlines]
  );

  const weekAgenda = useMemo(
    () =>
      [...upcomingDeadlines]
        .sort((a, b) => parseDate(a.due_date).getTime() - parseDate(b.due_date).getTime())
        .slice(0, 6),
    [upcomingDeadlines]
  );

  const focusItems = useMemo<FocusItem[]>(() => {
    const items: FocusItem[] = [
      {
        id: 'deadlines-today',
        label: 'obrigações vencem hoje',
        value: todaysDeadlines.length,
        tone: todaysDeadlines.length > 0 ? 'danger' : 'success',
      },
      {
        id: 'deadlines-overdue',
        label: 'obrigações em atraso',
        value: data?.overdue_deadlines ?? 0,
        tone: (data?.overdue_deadlines ?? 0) > 0 ? 'danger' : 'success',
      },
      {
        id: 'docs-review',
        label: 'documentos aguardando conferência',
        value: prod?.docs_awaiting_approval ?? 0,
        tone: (prod?.docs_awaiting_approval ?? 0) > 0 ? 'warning' : 'success',
      },
      {
        id: 'certificates',
        label: 'certificados vencendo em 30 dias',
        value: data?.certificates_expiring_30d ?? prod?.certificates_expiring_30d ?? 0,
        tone:
          (data?.certificates_expiring_30d ?? prod?.certificates_expiring_30d ?? 0) > 0
            ? 'warning'
            : 'info',
      },
    ];

    return items.filter((item) => item.value > 0).slice(0, 3);
  }, [data?.certificates_expiring_30d, data?.overdue_deadlines, prod?.certificates_expiring_30d, prod?.docs_awaiting_approval, todaysDeadlines.length]);

  const totalFocusCount = focusItems.reduce((sum, item) => sum + item.value, 0);

  const attentionClients = useMemo<AttentionItem[]>(() => {
    const fromPending =
      prod?.clients_with_most_pending.map<AttentionItem>((client) => ({
        id: `pending-${client.client_id}`,
        clientName: client.client_name,
        reason:
          client.pending_count === 1
            ? '1 pendência operacional aberta'
            : `${client.pending_count} pendências operacionais abertas`,
        level: client.pending_count >= 3 ? 'alto' : 'medio',
        actionLabel: 'Ver obrigações',
        actionPath: '/obrigacoes',
      })) ?? [];

    const fromOverdueReceivables = recentReceivables
      .filter((item) => item.status === 'overdue')
      .map((item) => ({
        id: `receivable-${item.id}`,
        clientName: item.client_name,
        reason: `recebível em atraso de ${moneyBRL(item.amount)}`,
        level: 'medio' as const,
        actionLabel: 'Abrir financeiro',
        actionPath: '/financeiro',
      }));

    const unique = new Map<string, AttentionItem>();

    [...fromPending, ...fromOverdueReceivables].forEach((item) => {
      if (!unique.has(item.clientName)) {
        unique.set(item.clientName, item);
      }
    });

    return Array.from(unique.values()).slice(0, 5);
  }, [prod?.clients_with_most_pending, recentReceivables]);

  const quickMetrics = [
    {
      label: 'Obrigações em aberto',
      value: isLoading ? '...' : String(data?.pending_deadlines ?? 0),
      detail: `${data?.overdue_deadlines ?? 0} atrasadas`,
      icon: CalendarClock,
    },
    {
      label: 'Clientes com atenção',
      value: isLoading ? '...' : String(attentionClients.length),
      detail: 'priorizar contato e regularização',
      icon: UsersRound,
    },
    {
      label: 'Documentos em fila',
      value: isLoading ? '...' : String(prod?.docs_awaiting_approval ?? 0),
      detail: 'aguardando conferência',
      icon: FileCheck2,
    },
    {
      label: 'Recebíveis em atraso',
      value: isLoading ? '...' : String(data?.overdue_receivables ?? 0),
      detail: moneyBRL(data?.receivables_amount_overdue ?? 0),
      icon: ReceiptText,
    },
  ];

  const officeSnapshot = [
    {
      label: 'Taxa de cumprimento',
      value: prod ? `${prod.compliance_rate}%` : '—',
      detail: prod ? `${prod.total_delivered} entregues no ciclo` : 'Sem dados',
      tone:
        (prod?.compliance_rate ?? 0) >= 80
          ? 'text-emerald-300'
          : (prod?.compliance_rate ?? 0) >= 50
            ? 'text-amber-200'
            : 'text-red-200',
    },
    {
      label: 'Em andamento',
      value: prod ? String(prod.total_pending + prod.total_in_progress) : '—',
      detail: prod ? `${prod.total_in_progress} em execução agora` : 'Sem dados',
      tone: 'text-slate-100',
    },
    {
      label: 'Receita recebida no mês',
      value: isLoading ? '...' : moneyBRL(data?.total_received_month ?? 0),
      detail: isLoading ? '...' : `${data?.active_clients ?? 0} clientes ativos`,
      tone: 'text-slate-100',
    },
  ];

  return (
    <div
      className="min-h-full rounded-[32px] border border-white/5 bg-[#0b111b] text-white"
      style={{
        backgroundImage:
          'radial-gradient(circle at top left, rgba(14,165,233,0.16), transparent 28%), radial-gradient(circle at top right, rgba(251,191,36,0.10), transparent 24%)',
      }}
    >
      <motion.div
        variants={containerVariants}
        initial="hidden"
        animate="show"
        className="mx-auto max-w-[1400px] space-y-6 p-5 md:p-8"
      >
        <SectionCard className="overflow-hidden bg-[linear-gradient(135deg,#102033_0%,#0f1724_52%,#15283a_100%)]">
          <div className="grid gap-8 p-6 md:grid-cols-[1.55fr_0.95fr] md:p-8">
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-cyan-200/90">
                Painel
              </p>
              <h1 className="mt-3 max-w-3xl text-3xl font-semibold tracking-tight text-white md:text-[2.8rem]">
                Veja o que precisa da sua atenção hoje
              </h1>
              <p className="mt-4 max-w-2xl text-sm leading-7 text-slate-300 md:text-base">
                Mantenha seus clientes em dia acompanhando obrigações, documentos pendentes e prazos fiscais em um só lugar.
              </p>

              <div className="mt-6 flex flex-wrap gap-3">
                <button
                  type="button"
                  onClick={() => navigate('/obrigacoes')}
                  className="inline-flex items-center gap-2 rounded-full bg-cyan-300 px-5 py-3 text-sm font-semibold text-slate-950 transition hover:-translate-y-0.5 hover:bg-cyan-200"
                >
                  Resolver agora
                  <ArrowRight className="h-4 w-4" />
                </button>
                <button
                  type="button"
                  onClick={() => navigate('/agenda-prazos')}
                  className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/5 px-5 py-3 text-sm font-semibold text-white transition hover:-translate-y-0.5 hover:bg-white/10"
                >
                  Ver agenda fiscal
                </button>
                <button
                  type="button"
                  onClick={() => navigate('/clientes', { state: { openCreate: true } })}
                  className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-transparent px-5 py-3 text-sm font-semibold text-slate-200 transition hover:-translate-y-0.5 hover:border-cyan-300/30 hover:text-white"
                >
                  Novo cliente
                </button>
              </div>

              {isError && (
                <div className="mt-6 flex items-center gap-3 rounded-2xl border border-amber-400/20 bg-amber-500/10 px-4 py-3 text-sm text-amber-100">
                  <AlertTriangle className="h-4 w-4 shrink-0" />
                  Não foi possível atualizar todo o painel agora. Os blocos abaixo usam os dados
                  mais recentes disponíveis.
                </div>
              )}
            </div>

            <div className="rounded-[26px] border border-white/10 bg-[#0b131f]/90 p-5 backdrop-blur">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-cyan-200/80">
                    Foco de hoje
                  </p>
                  <h2 className="mt-2 text-2xl font-semibold text-white">
                    {isLoading ? 'Carregando...' : `${totalFocusCount} itens pedem ação`}
                  </h2>
                </div>
                <div className="rounded-2xl border border-cyan-300/20 bg-cyan-300/10 p-3 text-cyan-200">
                  <Clock3 className="h-5 w-5" />
                </div>
              </div>

              <div className="mt-5 space-y-3">
                {focusItems.length === 0 ? (
                  <div className="rounded-2xl border border-emerald-400/20 bg-emerald-500/10 px-4 py-4 text-sm text-emerald-100">
                    Nenhuma urgência crítica agora. O painel segue limpo para acompanhar a semana.
                  </div>
                ) : (
                  focusItems.map((item) => (
                    <div
                      key={item.id}
                      className={`rounded-2xl border px-4 py-3 ${toneClasses(item.tone)}`}
                    >
                      <div className="flex items-center justify-between gap-4">
                        <p className="text-sm font-medium text-inherit">{item.label}</p>
                        <span className="text-lg font-semibold text-white">{item.value}</span>
                      </div>
                    </div>
                  ))
                )}
              </div>

              <div className="mt-5 rounded-2xl border border-white/10 bg-white/5 px-4 py-4">
                <p className="text-xs uppercase tracking-[0.18em] text-slate-400">Próximo passo</p>
                <p className="mt-2 text-sm leading-6 text-slate-200">
                  Comece pela agenda fiscal e depois avance para clientes com pendências abertas ou
                  documentos sem conferência.
                </p>
              </div>
            </div>
          </div>
        </SectionCard>

        <motion.section
          variants={containerVariants}
          className="grid gap-4 md:grid-cols-2 xl:grid-cols-4"
        >
          {quickMetrics.map((metric) => (
            <motion.div
              key={metric.label}
              variants={itemVariants}
              className="rounded-[24px] border border-white/8 bg-[#101826] px-5 py-5"
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-xs uppercase tracking-[0.18em] text-slate-400">{metric.label}</p>
                  <p className="mt-3 text-3xl font-semibold tracking-tight text-white">
                    {metric.value}
                  </p>
                  <p className="mt-2 text-sm text-slate-300">{metric.detail}</p>
                </div>
                <div className="rounded-2xl border border-white/10 bg-white/5 p-3 text-cyan-200">
                  <metric.icon className="h-5 w-5" />
                </div>
              </div>
            </motion.div>
          ))}
        </motion.section>

        <div className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
          <motion.div variants={containerVariants} className="space-y-6">
            <SectionCard className="p-6 md:p-7">
              <SectionHeader
                eyebrow="Atenção imediata"
                title="Clientes que precisam de atenção"
                description="A carteira mais sensível sobe primeiro: pendências operacionais e atrasos que podem virar retrabalho."
              />

              {attentionClients.length === 0 ? (
                <div className="rounded-[22px] border border-emerald-400/20 bg-emerald-500/10 px-5 py-6 text-sm text-emerald-100">
                  Nenhum cliente crítico no momento. Sua carteira está sob controle.
                </div>
              ) : (
                <div className="space-y-3">
                  {attentionClients.map((client) => (
                    <div
                      key={client.id}
                      className="flex flex-col gap-4 rounded-[22px] border border-white/8 bg-[#0c1420] px-5 py-4 md:flex-row md:items-center md:justify-between"
                    >
                      <div className="min-w-0">
                        <div className="flex flex-wrap items-center gap-3">
                          <p className="text-base font-semibold text-white">{client.clientName}</p>
                          <span
                            className={`rounded-full border px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.16em] ${badgeClasses(client.level)}`}
                          >
                            {client.level}
                          </span>
                        </div>
                        <p className="mt-2 text-sm leading-6 text-slate-300">{client.reason}</p>
                      </div>

                      <button
                        type="button"
                        onClick={() => navigate(client.actionPath)}
                        className="inline-flex shrink-0 items-center gap-2 self-start rounded-full border border-white/12 bg-white/5 px-4 py-2 text-sm font-semibold text-white transition hover:bg-white/10 md:self-center"
                      >
                        {client.actionLabel}
                        <ArrowRight className="h-4 w-4" />
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </SectionCard>

            <SectionCard className="p-6 md:p-7">
              <SectionHeader
                eyebrow="Agenda fiscal"
                title="Agenda da semana"
                description="Ordem de execução para não perder vencimentos nem deixar etapas críticas acumularem."
              />

              {weekAgenda.length === 0 ? (
                <div className="rounded-[22px] border border-white/8 bg-[#0c1420] px-5 py-6 text-sm text-slate-300">
                  Nenhum prazo futuro cadastrado. Cadastre as próximas obrigações para transformar o
                  painel em rotina operacional.
                </div>
              ) : (
                <div className="space-y-4">
                  {weekAgenda.map((deadline, index) => {
                    const distance = daysUntil(deadline.due_date);
                    const isCritical = deadline.priority === 'high' || distance <= 1;

                    return (
                      <div key={deadline.id} className="grid grid-cols-[auto_1fr] gap-4">
                        <div className="flex flex-col items-center">
                          <div
                            className={`mt-1 h-3 w-3 rounded-full ${isCritical ? 'bg-amber-300' : 'bg-cyan-300'}`}
                          />
                          {index < weekAgenda.length - 1 && (
                            <div className="mt-2 h-full min-h-8 w-px bg-white/10" />
                          )}
                        </div>

                        <div className="rounded-[22px] border border-white/8 bg-[#0c1420] px-5 py-4">
                          <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                            <div>
                              <div className="flex flex-wrap items-center gap-2">
                                <p className="text-base font-semibold text-white">{deadline.title}</p>
                                <span
                                  className={`rounded-full px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.16em] ${
                                    isCritical
                                      ? 'bg-amber-500/10 text-amber-100'
                                      : 'bg-cyan-500/10 text-cyan-100'
                                  }`}
                                >
                                  {formatDueLabel(distance)}
                                </span>
                              </div>
                              <p className="mt-2 text-sm leading-6 text-slate-300">
                                {deadline.category}
                              </p>
                            </div>

                            <div className="shrink-0">
                              <p className="text-sm font-medium text-white">{dateBR(deadline.due_date)}</p>
                              <p className="mt-1 text-xs uppercase tracking-[0.16em] text-slate-400">
                                prioridade {deadline.priority === 'high' ? 'alta' : deadline.priority}
                              </p>
                            </div>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </SectionCard>
          </motion.div>

          <motion.div variants={containerVariants} className="space-y-6">
            <SectionCard className="p-6">
              <SectionHeader
                eyebrow="Pendências"
                title="Fila operacional"
                description="Onde o dia costuma travar: documentos, certificados e recebíveis que exigem algum retorno."
              />

              <div className="space-y-3">
                <button
                  type="button"
                  onClick={() => navigate('/documentos')}
                  className="flex w-full items-center justify-between rounded-[20px] border border-white/8 bg-[#0c1420] px-4 py-4 text-left transition hover:bg-white/5"
                >
                  <div className="flex items-center gap-3">
                    <div className="rounded-2xl border border-white/10 bg-white/5 p-3 text-cyan-200">
                      <FileCheck2 className="h-4 w-4" />
                    </div>
                    <div>
                      <p className="text-sm font-semibold text-white">Documentos aguardando conferência</p>
                      <p className="mt-1 text-sm text-slate-300">
                        {prod?.docs_awaiting_approval ?? 0} item(ns) na fila
                      </p>
                    </div>
                  </div>
                  <ArrowRight className="h-4 w-4 text-slate-400" />
                </button>

                <button
                  type="button"
                  onClick={() => navigate('/certificados')}
                  className="flex w-full items-center justify-between rounded-[20px] border border-white/8 bg-[#0c1420] px-4 py-4 text-left transition hover:bg-white/5"
                >
                  <div className="flex items-center gap-3">
                    <div className="rounded-2xl border border-white/10 bg-white/5 p-3 text-amber-200">
                      <ShieldAlert className="h-4 w-4" />
                    </div>
                    <div>
                      <p className="text-sm font-semibold text-white">Certificados em janela de renovação</p>
                      <p className="mt-1 text-sm text-slate-300">
                        {data?.certificates_expiring_30d ?? prod?.certificates_expiring_30d ?? 0} item(ns) próximos do vencimento
                      </p>
                    </div>
                  </div>
                  <ArrowRight className="h-4 w-4 text-slate-400" />
                </button>

                <button
                  type="button"
                  onClick={() => navigate('/financeiro')}
                  className="flex w-full items-center justify-between rounded-[20px] border border-white/8 bg-[#0c1420] px-4 py-4 text-left transition hover:bg-white/5"
                >
                  <div className="flex items-center gap-3">
                    <div className="rounded-2xl border border-white/10 bg-white/5 p-3 text-red-200">
                      <ReceiptText className="h-4 w-4" />
                    </div>
                    <div>
                      <p className="text-sm font-semibold text-white">Recebíveis em atraso</p>
                      <p className="mt-1 text-sm text-slate-300">
                        {data?.overdue_receivables ?? 0} item(ns) somando {moneyBRL(data?.receivables_amount_overdue ?? 0)}
                      </p>
                    </div>
                  </div>
                  <ArrowRight className="h-4 w-4 text-slate-400" />
                </button>
              </div>
            </SectionCard>

            <SectionCard className="p-6">
              <SectionHeader
                eyebrow="Contexto"
                title="Resumo do escritório"
                description="Financeiro e produtividade seguem visíveis, mas como suporte à operação do dia."
              />

              <div className="space-y-3">
                {officeSnapshot.map((item) => (
                  <div
                    key={item.label}
                    className="rounded-[20px] border border-white/8 bg-[#0c1420] px-4 py-4"
                  >
                    <p className="text-xs uppercase tracking-[0.16em] text-slate-400">{item.label}</p>
                    <p className={`mt-2 text-2xl font-semibold ${item.tone}`}>{item.value}</p>
                    <p className="mt-2 text-sm text-slate-300">{item.detail}</p>
                  </div>
                ))}
              </div>
            </SectionCard>

            {isAdmin && (
              <SectionCard className="p-6">
                <SectionHeader
                  eyebrow="Visão interna"
                  title="Produtividade do time"
                  description="Leitura resumida por competência, com menos protagonismo visual do que no painel anterior."
                />

                <div className="grid gap-3">
                  <div className="rounded-[20px] border border-white/8 bg-[#0c1420] px-4 py-4">
                    <div className="flex items-center justify-between gap-3">
                      <div>
                        <p className="text-sm font-semibold text-white">Competência</p>
                        <p className="mt-1 text-sm text-slate-300">
                          {prod?.competence_month ?? 'Sem dados'}
                        </p>
                      </div>
                      <Users2 className="h-5 w-5 text-cyan-200" />
                    </div>
                  </div>

                  <div className="rounded-[20px] border border-white/8 bg-[#0c1420] px-4 py-4">
                    <div className="flex items-center justify-between gap-3">
                      <div>
                        <p className="text-sm font-semibold text-white">Obrigações vencidas</p>
                        <p className="mt-1 text-sm text-slate-300">
                          {prod?.total_overdue ?? 0} no ciclo atual
                        </p>
                      </div>
                      <AlertTriangle className="h-5 w-5 text-amber-200" />
                    </div>
                  </div>

                  <div className="rounded-[20px] border border-white/8 bg-[#0c1420] px-4 py-4">
                    <div className="flex items-center justify-between gap-3">
                      <div>
                        <p className="text-sm font-semibold text-white">Entregues</p>
                        <p className="mt-1 text-sm text-slate-300">
                          {prod?.total_delivered ?? 0} concluídas
                        </p>
                      </div>
                      <CheckCircle2 className="h-5 w-5 text-emerald-200" />
                    </div>
                  </div>
                </div>
              </SectionCard>
            )}
          </motion.div>
        </div>
      </motion.div>
    </div>
  );
}
