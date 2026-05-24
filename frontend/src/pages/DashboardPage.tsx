import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  AreaChart,
  Area,
} from 'recharts';
import {
  UsersRound,
  CalendarClock,
  ShieldAlert,
  ReceiptText,
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  CheckCircle2,
  Clock3,
  FileCheck2,
  Users2,
} from 'lucide-react';
import { dateBR, moneyBRL, useDashboardOverview, useProductivityOverview } from '@/lib/hooks/useOperations';
import { usePermission } from '@/lib/hooks/usePermission';

// ─── Variantes de animação ────────────────────────────────────────────────────
const containerVariants = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.08 },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0, transition: { duration: 0.5, ease: 'easeOut' as const } },
};

const cardHover = {
  y: -4,
  boxShadow: '0 10px 40px rgba(0, 212, 255, 0.12)',
  borderColor: 'rgba(0, 212, 255, 0.25)',
  transition: { duration: 0.25 },
};

// ─── Custom Tooltip para Recharts ─────────────────────────────────────────────
function CustomTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: Array<{ name: string; value: number; color: string }>;
  label?: string;
}) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-xl border border-[rgba(0,212,255,0.2)] bg-[#1a1f2e] p-3 shadow-xl">
      <p className="mb-2 text-xs font-semibold uppercase tracking-widest text-[#7a8490]">{label}</p>
      {payload.map((entry) => (
        <p key={entry.name} className="text-sm font-semibold" style={{ color: entry.color }}>
          {entry.name}: {moneyBRL(entry.value)}
        </p>
      ))}
    </div>
  );
}

// ─── Componente MetricCard ────────────────────────────────────────────────────
interface MetricCardProps {
  title: string;
  value: string | number;
  change: string;
  positive: boolean;
  icon: React.ElementType;
  delay?: number;
}

function MetricCard({ title, value, change, positive, icon: Icon, delay = 0 }: MetricCardProps) {
  return (
    <motion.div
      variants={itemVariants}
      whileHover={cardHover}
      style={{ transitionDelay: `${delay}ms` }}
      className="relative overflow-hidden rounded-xl border border-white/[0.08] bg-[#1a1f2e] p-6 cursor-default"
    >
      {/* top accent line on hover - always rendered, opacity controlled by group */}
      <div
        className="pointer-events-none absolute inset-x-0 top-0 h-[2px]"
        style={{
          background: 'linear-gradient(90deg, transparent, #00d4ff, transparent)',
          opacity: 0.6,
        }}
      />

      <div className="mb-4 flex items-center justify-between">
        <span className="text-xs font-semibold uppercase tracking-widest text-[#7a8490]">
          {title}
        </span>
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-[rgba(0,212,255,0.1)] border border-[rgba(0,212,255,0.15)]">
          <Icon className="h-4 w-4 text-[#00d4ff]" />
        </div>
      </div>

      <div
        className="text-3xl font-bold tracking-tight"
        style={{
          background: 'linear-gradient(135deg, #ffffff, #b4bcc4)',
          WebkitBackgroundClip: 'text',
          WebkitTextFillColor: 'transparent',
          backgroundClip: 'text',
        }}
      >
        {value}
      </div>

      <div className={`mt-2 flex items-center gap-1 text-sm font-medium ${positive ? 'text-emerald-400' : 'text-red-400'}`}>
        {positive ? <TrendingUp className="h-3.5 w-3.5" /> : <TrendingDown className="h-3.5 w-3.5" />}
        {change}
      </div>
    </motion.div>
  );
}

// ─── Helpers de status para recebíveis ───────────────────────────────────────
function statusLabel(s: string) {
  if (s === 'paid') return 'Recebido';
  if (s === 'overdue') return 'Atrasado';
  return 'Pendente';
}

function statusClass(s: string) {
  if (s === 'paid') return 'bg-emerald-500/10 text-emerald-400';
  if (s === 'overdue') return 'bg-red-500/10 text-red-400';
  return 'bg-amber-500/10 text-amber-400';
}

export function DashboardPage() {
  const { data, isLoading, isError } = useDashboardOverview();
  const navigate = useNavigate();
  const { hasRole } = usePermission();
  const isAdminOrOwner = hasRole('admin');
  const { data: prod } = useProductivityOverview();

  const weeklyData = data?.weekly_received ?? [];
  const monthlyTrend = data?.monthly_received ?? [];
  const recentReceivables = data?.recent_receivables ?? [];

  const metricsCards: MetricCardProps[] = [
    {
      title: 'Receita total',
      value: isLoading ? '...' : moneyBRL(data?.total_received_month),
      change: 'Recebido no mês corrente',
      positive: true,
      icon: TrendingUp,
      delay: 0,
    },
    {
      title: 'A receber (aberto)',
      value: isLoading ? '...' : moneyBRL(data?.receivables_amount_open),
      change: `${data?.open_receivables ?? 0} recebíveis em aberto`,
      positive: true,
      icon: ReceiptText,
      delay: 80,
    },
    {
      title: 'Inadimplência',
      value: isLoading ? '...' : moneyBRL(data?.receivables_amount_overdue),
      change: `${data?.overdue_receivables ?? 0} em atraso`,
      positive: (data?.overdue_receivables ?? 0) === 0,
      icon: TrendingDown,
      delay: 160,
    },
    {
      title: 'Clientes ativos',
      value: isLoading ? '...' : String(data?.active_clients ?? 0),
      change: 'Total na plataforma',
      positive: true,
      icon: UsersRound,
      delay: 240,
    },
  ];

  return (
    <div
      className="min-h-screen"
      style={{ background: '#0f1419', color: '#ffffff' }}
    >
      <div className="mx-auto max-w-[1400px] space-y-8 p-6 md:p-8">

        {/* ── Hero ── */}
        <motion.section
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, ease: 'easeOut' }}
          className="mb-2"
        >
          <h1 className="text-3xl font-bold tracking-tight md:text-4xl">
            Bem-vindo de volta!{' '}
            <span
              style={{
                background: 'linear-gradient(135deg, #00d4ff, #00f0ff)',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
                backgroundClip: 'text',
              }}
            >
              FiscWise
            </span>
          </h1>
          <p className="mt-2 text-base text-[#b4bcc4]">
            Suas operações financeiras em tempo real, com total clareza e controle.
          </p>

          <div className="mt-5 flex flex-wrap gap-3">
            {/* Novo cliente → /clientes com dialog aberto */}
            <motion.button
              whileHover={{ y: -2, boxShadow: '0 0 30px rgba(0,212,255,0.45)' }}
              whileTap={{ scale: 0.97 }}
              onClick={() => navigate('/clientes', { state: { openCreate: true } })}
              className="rounded-lg px-5 py-2.5 text-sm font-semibold text-[#0f1419] transition-all"
              style={{
                background: 'linear-gradient(135deg, #00d4ff, #00f0ff)',
                boxShadow: '0 0 20px rgba(0,212,255,0.3)',
              }}
            >
              + Novo cliente
            </motion.button>

            {/* Novo recebível → /financeiro com dialog aberto */}
            <motion.button
              whileHover={{ y: -2, boxShadow: '0 0 30px rgba(0,212,255,0.45)' }}
              whileTap={{ scale: 0.97 }}
              onClick={() => navigate('/financeiro', { state: { openCreate: true } })}
              className="rounded-lg px-5 py-2.5 text-sm font-semibold text-[#0f1419] transition-all"
              style={{
                background: 'linear-gradient(135deg, #00d4ff, #00f0ff)',
                boxShadow: '0 0 20px rgba(0,212,255,0.3)',
              }}
            >
              + Novo recebível
            </motion.button>

            {/* Ver relatório → /financeiro */}
            <motion.button
              whileHover={{ y: -2, backgroundColor: 'rgba(0,212,255,0.1)' }}
              whileTap={{ scale: 0.97 }}
              onClick={() => navigate('/financeiro')}
              className="rounded-lg border border-[rgba(0,212,255,0.25)] bg-transparent px-5 py-2.5 text-sm font-semibold text-[#00d4ff] transition-all"
            >
              Ver relatório
            </motion.button>
          </div>
        </motion.section>

        {/* ── Error banner ── */}
        {isError && (
          <motion.div
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            className="flex items-center gap-3 rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400"
          >
            <AlertTriangle className="h-4 w-4 shrink-0" />
            Não foi possível carregar os dados operacionais agora. Exibindo valores demonstrativos.
          </motion.div>
        )}

        {/* ── Metric Cards ── */}
        <motion.div
          variants={containerVariants}
          initial="hidden"
          animate="show"
          className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4"
        >
          {metricsCards.map((card) => (
            <MetricCard key={card.title} {...card} />
          ))}
        </motion.div>

        {/* ── KPI operacional (dados reais) ── */}
        <motion.div
          variants={containerVariants}
          initial="hidden"
          animate="show"
          className="grid gap-4 sm:grid-cols-3"
        >
          {[
            {
              title: 'Prazos pendentes',
              value: isLoading ? '...' : String(data?.pending_deadlines ?? 0),
              sub: `${data?.overdue_deadlines ?? 0} atrasados`,
              icon: CalendarClock,
              warn: (data?.overdue_deadlines ?? 0) > 0,
            },
            {
              title: 'Certificados 30 dias',
              value: isLoading ? '...' : String(data?.certificates_expiring_30d ?? 0),
              sub: 'Renovações próximas',
              icon: ShieldAlert,
              warn: (data?.certificates_expiring_30d ?? 0) > 0,
            },
            {
              title: 'A receber (aberto)',
              value: isLoading ? '...' : moneyBRL(data?.receivables_amount_open),
              sub: `${data?.overdue_receivables ?? 0} em atraso`,
              icon: ReceiptText,
              warn: (data?.overdue_receivables ?? 0) > 0,
            },
          ].map((kpi, i) => (
            <motion.div
              key={kpi.title}
              variants={itemVariants}
              whileHover={cardHover}
              custom={i}
              className="relative overflow-hidden rounded-xl border border-white/[0.08] bg-[#1a1f2e] p-5"
            >
              <div
                className="pointer-events-none absolute inset-x-0 top-0 h-[2px]"
                style={{
                  background: kpi.warn
                    ? 'linear-gradient(90deg, transparent, #f59e0b, transparent)'
                    : 'linear-gradient(90deg, transparent, #00d4ff, transparent)',
                  opacity: 0.5,
                }}
              />
              <div className="mb-3 flex items-center justify-between">
                <span className="text-xs font-semibold uppercase tracking-widest text-[#7a8490]">
                  {kpi.title}
                </span>
                <kpi.icon
                  className={`h-4 w-4 ${kpi.warn ? 'text-amber-400' : 'text-[#00d4ff]'}`}
                />
              </div>
              <div
                className="text-2xl font-bold"
                style={{
                  background: 'linear-gradient(135deg, #ffffff, #b4bcc4)',
                  WebkitBackgroundClip: 'text',
                  WebkitTextFillColor: 'transparent',
                  backgroundClip: 'text',
                }}
              >
                {kpi.value}
              </div>
              <p className={`mt-1 text-xs font-medium ${kpi.warn ? 'text-amber-400' : 'text-[#7a8490]'}`}>
                {kpi.sub}
              </p>
            </motion.div>
          ))}
        </motion.div>

        {/* ── Charts Row ── */}
        <div className="grid gap-6 lg:grid-cols-5">

          {/* Bar Chart – Receita semanal */}
          <motion.div
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.2 }}
            className="lg:col-span-3 rounded-xl border border-white/[0.08] bg-[#1a1f2e] p-6"
          >
            <div className="mb-5 flex items-start justify-between border-b border-white/[0.06] pb-4">
              <div>
                <h3 className="text-base font-bold text-white">Receita por dia</h3>
                <p className="mt-0.5 text-xs text-[#7a8490]">Últimos 7 dias</p>
              </div>
              <span
                className="rounded-full border border-[rgba(0,212,255,0.25)] bg-[rgba(0,212,255,0.08)] px-3 py-1 text-[10px] font-bold uppercase tracking-widest text-[#00d4ff]"
              >
                Em tempo real
              </span>
            </div>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={weeklyData} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                <XAxis
                  dataKey="dia"
                  tick={{ fill: '#7a8490', fontSize: 11 }}
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis
                  tick={{ fill: '#7a8490', fontSize: 11 }}
                  axisLine={false}
                  tickLine={false}
                  tickFormatter={(v: number) => `${(v / 1000).toFixed(0)}k`}
                />
                <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(0,212,255,0.05)' }} />
                <Bar
                  dataKey="receita"
                  name="Receita"
                  fill="url(#barGradient)"
                  radius={[5, 5, 0, 0]}
                  maxBarSize={42}
                />
                {/* Barra de despesa removida — sem modelo de despesas no sistema */}
                <defs>
                  <linearGradient id="barGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#00f0ff" stopOpacity={0.9} />
                    <stop offset="100%" stopColor="#00d4ff" stopOpacity={0.5} />
                  </linearGradient>
                </defs>
              </BarChart>
            </ResponsiveContainer>
          </motion.div>

          {/* Area Chart – Tendência mensal */}
          <motion.div
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.35 }}
            className="lg:col-span-2 rounded-xl border border-white/[0.08] bg-[#1a1f2e] p-6"
          >
            <div className="mb-5 border-b border-white/[0.06] pb-4">
              <h3 className="text-base font-bold text-white">Tendência mensal</h3>
              <p className="mt-0.5 text-xs text-[#7a8490]">Receita acumulada 2026</p>
            </div>
            <ResponsiveContainer width="100%" height={220}>
              <AreaChart data={monthlyTrend} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="areaGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#00d4ff" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#00d4ff" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                <XAxis
                  dataKey="mes"
                  tick={{ fill: '#7a8490', fontSize: 11 }}
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis
                  tick={{ fill: '#7a8490', fontSize: 11 }}
                  axisLine={false}
                  tickLine={false}
                  tickFormatter={(v: number) => `${(v / 1000).toFixed(0)}k`}
                />
                <Tooltip content={<CustomTooltip />} cursor={{ stroke: 'rgba(0,212,255,0.3)' }} />
                <Area
                  type="monotone"
                  dataKey="valor"
                  name="Receita"
                  stroke="#00d4ff"
                  strokeWidth={2}
                  fill="url(#areaGradient)"
                  dot={{ fill: '#00d4ff', r: 3 }}
                  activeDot={{ r: 5, fill: '#00f0ff' }}
                />
              </AreaChart>
            </ResponsiveContainer>
          </motion.div>
        </div>

        {/* ── Próximos prazos + Risco financeiro ── */}
        <div className="grid gap-6 lg:grid-cols-3">
          {/* Próximos prazos */}
          <motion.div
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.4 }}
            className="lg:col-span-2 rounded-xl border border-white/[0.08] bg-[#1a1f2e] overflow-hidden"
          >
            <div className="border-b border-white/[0.06] bg-[#141824] px-6 py-4">
              <h3 className="text-base font-bold text-white">Próximos prazos</h3>
            </div>
            <div className="divide-y divide-white/[0.04] px-6">
              {(data?.upcoming_deadlines ?? []).length === 0 ? (
                <p className="py-6 text-sm text-[#7a8490]">
                  Nenhum prazo futuro cadastrado. Cadastre o primeiro prazo em Agenda e Prazos.
                </p>
              ) : (
                (data?.upcoming_deadlines ?? []).map((deadline) => (
                  <div key={deadline.id} className="flex items-start justify-between gap-4 py-4">
                    <div className="min-w-0">
                      <p className="font-semibold text-white">{deadline.title}</p>
                      <p className="mt-0.5 truncate text-sm text-[#7a8490]">{deadline.category}</p>
                    </div>
                    <div className="shrink-0 text-right">
                      <p className="text-sm font-medium text-white">{dateBR(deadline.due_date)}</p>
                      <span
                        className={`mt-1 inline-block rounded px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide ${
                          deadline.priority === 'high'
                            ? 'bg-red-500/10 text-red-400'
                            : 'bg-amber-500/10 text-amber-400'
                        }`}
                      >
                        {deadline.priority === 'high' ? 'Alta' : 'Acompanhar'}
                      </span>
                    </div>
                  </div>
                ))
              )}
            </div>
          </motion.div>

          {/* Risco financeiro */}
          <motion.div
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.5 }}
            className="rounded-xl border border-white/[0.08] bg-[#1a1f2e] overflow-hidden"
          >
            <div className="border-b border-white/[0.06] bg-[#141824] px-6 py-4">
              <h3 className="text-base font-bold text-white">Risco financeiro</h3>
            </div>
            <div className="space-y-4 p-6">
              <div className="rounded-lg border border-white/[0.06] bg-[#141824] p-4">
                <p className="text-xs text-[#7a8490]">Valor vencido</p>
                <p
                  className="mt-2 text-2xl font-bold"
                  style={{
                    background: 'linear-gradient(135deg, #ef4444, #fca5a5)',
                    WebkitBackgroundClip: 'text',
                    WebkitTextFillColor: 'transparent',
                    backgroundClip: 'text',
                  }}
                >
                  {isLoading ? '...' : moneyBRL(data?.receivables_amount_overdue)}
                </p>
              </div>
              <div className="rounded-lg border border-white/[0.06] bg-[#141824] p-4">
                <p className="text-xs text-[#7a8490]">Recebíveis em aberto</p>
                <p
                  className="mt-2 text-2xl font-bold"
                  style={{
                    background: 'linear-gradient(135deg, #ffffff, #b4bcc4)',
                    WebkitBackgroundClip: 'text',
                    WebkitTextFillColor: 'transparent',
                    backgroundClip: 'text',
                  }}
                >
                  {isLoading ? '...' : String(data?.open_receivables ?? 0)}
                </p>
              </div>
            </div>
          </motion.div>
        </div>

        {/* ── Tabela de transações recentes ── */}
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.55 }}
          className="rounded-xl border border-white/[0.08] bg-[#1a1f2e] overflow-hidden"
        >
          <div className="border-b border-white/[0.06] bg-[#141824] px-6 py-4">
            <h3 className="text-base font-bold text-white">Movimentações recentes</h3>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="bg-[#141824]">
                  {['Cliente / Descrição', 'Tipo', 'Valor', 'Data', 'Status'].map((h) => (
                    <th
                      key={h}
                      className="border-b border-white/[0.06] px-6 py-3 text-left text-[10px] font-bold uppercase tracking-widest text-[#7a8490]"
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {recentReceivables.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="px-6 py-8 text-center text-sm text-[#7a8490]">
                      Nenhuma movimentação encontrada. Cadastre recebíveis em Financeiro.
                    </td>
                  </tr>
                ) : (
                  recentReceivables.map((item, i) => (
                    <motion.tr
                      key={item.id}
                      initial={{ opacity: 0, x: -8 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ duration: 0.35, delay: 0.6 + i * 0.07 }}
                      className="group border-b border-white/[0.04] transition-colors last:border-0 hover:bg-[rgba(0,212,255,0.04)]"
                    >
                      <td className="px-6 py-4">
                        <p className="font-semibold text-white">{item.client_name}</p>
                        <p className="mt-0.5 text-sm text-[#7a8490]">{item.description}</p>
                      </td>
                      <td className="px-6 py-4 text-sm text-[#b4bcc4]">Recebível</td>
                      <td className="px-6 py-4 text-sm font-semibold text-emerald-400">
                        {moneyBRL(item.amount)}
                      </td>
                      <td className="px-6 py-4 text-sm text-[#b4bcc4]">{dateBR(item.due_date)}</td>
                      <td className="px-6 py-4">
                        <span
                          className={`inline-block rounded px-2.5 py-1 text-[10px] font-bold uppercase tracking-wide ${statusClass(item.status)}`}
                        >
                          {statusLabel(item.status)}
                        </span>
                      </td>
                    </motion.tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </motion.div>

        {/* ── Painel de Produtividade (owner/admin apenas) ── */}
        {isAdminOrOwner && (
          <motion.section
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.6 }}
          >
            {/* Header */}
            <div className="mb-4 flex items-center gap-3">
              <div
                className="flex h-8 w-8 items-center justify-center rounded-lg"
                style={{ background: 'rgba(0,212,255,0.1)', border: '1px solid rgba(0,212,255,0.2)' }}
              >
                <Users2 className="h-4 w-4 text-[#00d4ff]" />
              </div>
              <div>
                <h2 className="text-base font-bold text-white">Painel de Produtividade</h2>
                <p className="text-xs text-[#7a8490]">
                  Competência {prod?.competence_month ?? '—'} · Visível apenas para administradores
                </p>
              </div>
            </div>

            {/* KPI row */}
            <div className="mb-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              {/* Compliance rate */}
              <div className="rounded-xl border border-white/[0.08] bg-[#1a1f2e] p-4">
                <div className="mb-2 flex items-center justify-between">
                  <span className="text-[10px] font-bold uppercase tracking-widest text-[#7a8490]">Taxa de cumprimento</span>
                  <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                </div>
                <p
                  className="text-2xl font-bold"
                  style={{
                    background:
                      (prod?.compliance_rate ?? 0) >= 80
                        ? 'linear-gradient(135deg, #34d399, #6ee7b7)'
                        : (prod?.compliance_rate ?? 0) >= 50
                        ? 'linear-gradient(135deg, #fbbf24, #fde68a)'
                        : 'linear-gradient(135deg, #f87171, #fca5a5)',
                    WebkitBackgroundClip: 'text',
                    WebkitTextFillColor: 'transparent',
                    backgroundClip: 'text',
                  }}
                >
                  {prod ? `${prod.compliance_rate}%` : '—'}
                </p>
                <p className="mt-1 text-xs text-[#7a8490]">
                  {prod ? `${prod.total_delivered} entregues / ${prod.total_delivered + prod.total_overdue} fechadas` : 'Sem dados'}
                </p>
              </div>

              {/* Pending */}
              <div className="rounded-xl border border-white/[0.08] bg-[#1a1f2e] p-4">
                <div className="mb-2 flex items-center justify-between">
                  <span className="text-[10px] font-bold uppercase tracking-widest text-[#7a8490]">Em aberto</span>
                  <Clock3 className="h-4 w-4 text-amber-400" />
                </div>
                <p
                  className="text-2xl font-bold"
                  style={{
                    background: 'linear-gradient(135deg, #ffffff, #b4bcc4)',
                    WebkitBackgroundClip: 'text',
                    WebkitTextFillColor: 'transparent',
                    backgroundClip: 'text',
                  }}
                >
                  {prod ? prod.total_pending + prod.total_in_progress : '—'}
                </p>
                <p className="mt-1 text-xs text-[#7a8490]">
                  {prod ? `${prod.total_pending} pendentes · ${prod.total_in_progress} em andamento` : 'Sem dados'}
                </p>
              </div>

              {/* Docs awaiting approval */}
              <div className="rounded-xl border border-white/[0.08] bg-[#1a1f2e] p-4">
                <div className="mb-2 flex items-center justify-between">
                  <span className="text-[10px] font-bold uppercase tracking-widest text-[#7a8490]">Docs aguardando aprovação</span>
                  <FileCheck2 className="h-4 w-4 text-[#00d4ff]" />
                </div>
                <p
                  className="text-2xl font-bold"
                  style={{
                    background: 'linear-gradient(135deg, #ffffff, #b4bcc4)',
                    WebkitBackgroundClip: 'text',
                    WebkitTextFillColor: 'transparent',
                    backgroundClip: 'text',
                  }}
                >
                  {prod ? prod.docs_awaiting_approval : '—'}
                </p>
                <p className="mt-1 text-xs text-[#7a8490]">Recebidos, aguardando conferência</p>
              </div>

              {/* Overdue obligations */}
              <div className="rounded-xl border border-white/[0.08] bg-[#1a1f2e] p-4">
                <div className="mb-2 flex items-center justify-between">
                  <span className="text-[10px] font-bold uppercase tracking-widest text-[#7a8490]">Obrigações vencidas</span>
                  <AlertTriangle className="h-4 w-4 text-red-400" />
                </div>
                <p
                  className="text-2xl font-bold"
                  style={{
                    background:
                      (prod?.total_overdue ?? 0) > 0
                        ? 'linear-gradient(135deg, #f87171, #fca5a5)'
                        : 'linear-gradient(135deg, #34d399, #6ee7b7)',
                    WebkitBackgroundClip: 'text',
                    WebkitTextFillColor: 'transparent',
                    backgroundClip: 'text',
                  }}
                >
                  {prod ? prod.total_overdue : '—'}
                </p>
                <p className="mt-1 text-xs text-[#7a8490]">No mês de competência atual</p>
              </div>
            </div>

            {/* Collaborators + Top pending clients */}
            <div className="grid gap-4 lg:grid-cols-2">
              {/* Obligations by collaborator */}
              <div className="rounded-xl border border-white/[0.08] bg-[#1a1f2e] overflow-hidden">
                <div className="border-b border-white/[0.06] bg-[#141824] px-5 py-3">
                  <h3 className="text-sm font-bold text-white">Obrigações por colaborador</h3>
                </div>
                <div className="divide-y divide-white/[0.04]">
                  {!prod || prod.obligations_by_collaborator.length === 0 ? (
                    <p className="px-5 py-6 text-sm text-[#7a8490]">
                      Nenhuma obrigação atribuída neste mês. Atribua responsáveis na página de Obrigações.
                    </p>
                  ) : (
                    prod.obligations_by_collaborator.map((collab) => {
                      const pct = collab.total > 0
                        ? Math.round((collab.delivered / collab.total) * 100)
                        : 0;
                      return (
                        <div key={collab.user_id ?? 'unassigned'} className="px-5 py-3">
                          <div className="mb-1.5 flex items-center justify-between">
                            <span className="text-sm font-medium text-white">{collab.user_name}</span>
                            <div className="flex items-center gap-2 text-xs">
                              <span className="text-emerald-400">{collab.delivered} ✓</span>
                              {collab.overdue > 0 && (
                                <span className="text-red-400">{collab.overdue} ✗</span>
                              )}
                              <span className="text-[#7a8490]">{collab.pending + collab.in_progress} abertos</span>
                            </div>
                          </div>
                          {/* Progress bar */}
                          <div className="h-1.5 w-full overflow-hidden rounded-full bg-white/[0.08]">
                            <div
                              className="h-full rounded-full transition-all duration-700"
                              style={{
                                width: `${pct}%`,
                                background:
                                  pct >= 80
                                    ? 'linear-gradient(90deg, #34d399, #6ee7b7)'
                                    : pct >= 50
                                    ? 'linear-gradient(90deg, #fbbf24, #fde68a)'
                                    : 'linear-gradient(90deg, #00d4ff, #00f0ff)',
                              }}
                            />
                          </div>
                        </div>
                      );
                    })
                  )}
                </div>
              </div>

              {/* Top pending clients */}
              <div className="rounded-xl border border-white/[0.08] bg-[#1a1f2e] overflow-hidden">
                <div className="border-b border-white/[0.06] bg-[#141824] px-5 py-3">
                  <h3 className="text-sm font-bold text-white">Clientes com mais pendências</h3>
                </div>
                <div className="divide-y divide-white/[0.04]">
                  {!prod || prod.clients_with_most_pending.length === 0 ? (
                    <p className="px-5 py-6 text-sm text-[#7a8490]">
                      Nenhuma obrigação pendente no mês. Ótimo desempenho!
                    </p>
                  ) : (
                    prod.clients_with_most_pending.map((client, idx) => (
                      <div key={client.client_id} className="flex items-center gap-3 px-5 py-3">
                        <span
                          className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-[10px] font-bold"
                          style={{
                            background:
                              idx === 0
                                ? 'rgba(251,191,36,0.15)'
                                : 'rgba(0,212,255,0.08)',
                            color: idx === 0 ? '#fbbf24' : '#00d4ff',
                            border: `1px solid ${idx === 0 ? 'rgba(251,191,36,0.3)' : 'rgba(0,212,255,0.2)'}`,
                          }}
                        >
                          {idx + 1}
                        </span>
                        <span className="min-w-0 flex-1 truncate text-sm font-medium text-white">
                          {client.client_name}
                        </span>
                        <span className="shrink-0 rounded px-2 py-0.5 text-[10px] font-bold bg-amber-500/10 text-amber-400">
                          {client.pending_count} pendente{client.pending_count !== 1 ? 's' : ''}
                        </span>
                      </div>
                    ))
                  )}
                </div>

                {/* Alert strip */}
                {prod && (prod.certificates_expiring_30d > 0 || prod.overdue_receivables_count > 0) && (
                  <div className="border-t border-white/[0.06] bg-[#141824] px-5 py-3 space-y-2">
                    {prod.certificates_expiring_30d > 0 && (
                      <div className="flex items-center gap-2 text-xs text-amber-400">
                        <ShieldAlert className="h-3.5 w-3.5 shrink-0" />
                        <span>
                          {prod.certificates_expiring_30d} certificado{prod.certificates_expiring_30d !== 1 ? 's' : ''} vencendo em 30 dias
                        </span>
                      </div>
                    )}
                    {prod.overdue_receivables_count > 0 && (
                      <div className="flex items-center gap-2 text-xs text-red-400">
                        <ReceiptText className="h-3.5 w-3.5 shrink-0" />
                        <span>
                          {prod.overdue_receivables_count} recebível{prod.overdue_receivables_count !== 1 ? 'is' : ''} em atraso
                          &nbsp;({moneyBRL(prod.overdue_receivables_amount)})
                        </span>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          </motion.section>
        )}

        {/* ── Footer ── */}
        <footer className="border-t border-white/[0.06] pt-6 text-center text-xs text-[#7a8490]">
          FiscWise © 2026 — Sistema de contabilidade inteligente
        </footer>
      </div>
    </div>
  );
}
