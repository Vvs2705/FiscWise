import { motion } from 'framer-motion';
import { Calendar, CheckCircle2, Clock, AlertCircle, XCircle } from 'lucide-react';
import { fadeIn } from '../../../lib/motion';

interface ClosingStats {
  completed: number;
  inProgress: number;
  blockedByClient: number;
  overdue: number;
  total: number;
  completionPercentage: number;
}

interface MonthlyClosingCardProps {
  month: string;
  year: number;
  stats: ClosingStats;
  isLoading?: boolean;
}

export function MonthlyClosingCard({
  month,
  year,
  stats,
  isLoading,
}: MonthlyClosingCardProps) {
  if (isLoading) {
    return (
      <div className="bg-fw-surface-solid border border-fw-border rounded-xl p-6">
        <div className="h-6 w-40 bg-fw-surface animate-pulse rounded mb-4" />
        <div className="h-32 bg-fw-surface animate-pulse rounded-lg" />
      </div>
    );
  }

  const progressColor =
    stats.completionPercentage >= 90
      ? 'bg-fw-success'
      : stats.completionPercentage >= 70
      ? 'bg-fw-blue'
      : stats.completionPercentage >= 50
      ? 'bg-fw-warning'
      : 'bg-fw-danger';

  const statusItems = [
    {
      label: 'Concluídos',
      value: stats.completed,
      icon: CheckCircle2,
      color: 'text-fw-success',
      bg: 'bg-fw-success-soft',
    },
    {
      label: 'Em andamento',
      value: stats.inProgress,
      icon: Clock,
      color: 'text-fw-blue',
      bg: 'bg-fw-blue-soft',
    },
    {
      label: 'Bloqueados',
      value: stats.blockedByClient,
      icon: AlertCircle,
      color: 'text-fw-warning',
      bg: 'bg-fw-warning-soft',
    },
    {
      label: 'Atrasados',
      value: stats.overdue,
      icon: XCircle,
      color: 'text-fw-danger',
      bg: 'bg-fw-danger-soft',
    },
  ];

  return (
    <motion.div
      variants={fadeIn}
      className="bg-fw-surface-solid border border-fw-border rounded-xl p-6"
    >
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-fw-text flex items-center gap-2">
          <Calendar className="w-5 h-5 text-fw-primary" />
          Fechamentos Mensais
        </h2>
        <span className="text-sm font-medium text-fw-text-muted">
          {month}/{year}
        </span>
      </div>

      {/* Progress Bar */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium text-fw-text">
            Progresso geral
          </span>
          <span className="text-2xl font-bold text-fw-text">
            {stats.completionPercentage}%
          </span>
        </div>
        <div className="h-3 bg-fw-surface rounded-full overflow-hidden">
          <motion.div
            initial={{ width: 0 }}
            animate={{ width: `${stats.completionPercentage}%` }}
            transition={{ duration: 1, ease: 'easeOut' }}
            className={`h-full ${progressColor} rounded-full`}
          />
        </div>
        <p className="text-xs text-fw-text-muted mt-2">
          {stats.completed} de {stats.total} fechamentos concluídos
        </p>
      </div>

      {/* Status Grid */}
      <div className="grid grid-cols-2 gap-3">
        {statusItems.map((item) => {
          const Icon = item.icon;
          return (
            <div
              key={item.label}
              className={`${item.bg} border border-fw-border rounded-lg p-3`}
            >
              <div className="flex items-center gap-2 mb-1">
                <Icon className={`w-4 h-4 ${item.color}`} />
                <span className="text-xs font-medium text-fw-text-muted">
                  {item.label}
                </span>
              </div>
              <p className={`text-2xl font-bold ${item.color}`}>
                {item.value}
              </p>
            </div>
          );
        })}
      </div>

      {/* Alert for overdue */}
      {stats.overdue > 0 && (
        <div className="mt-4 p-3 bg-fw-danger-soft border border-fw-danger/30 rounded-lg">
          <p className="text-sm font-medium text-fw-danger">
            {stats.overdue} fechamento{stats.overdue > 1 ? 's' : ''} atrasado
            {stats.overdue > 1 ? 's' : ''} precisa{stats.overdue > 1 ? 'm' : ''}{' '}
            de atenção
          </p>
        </div>
      )}
    </motion.div>
  );
}
