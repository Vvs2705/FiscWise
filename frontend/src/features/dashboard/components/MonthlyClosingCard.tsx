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
      <div className="bg-card border border-border rounded-card shadow-token-sm p-6">
        <div className="h-6 w-40 bg-muted animate-pulse rounded mb-4" />
        <div className="h-32 bg-muted animate-pulse rounded-lg" />
      </div>
    );
  }

  const progressColor =
    stats.completionPercentage >= 90
      ? 'bg-success'
      : stats.completionPercentage >= 70
      ? 'bg-info'
      : stats.completionPercentage >= 50
      ? 'bg-warning'
      : 'bg-destructive';

  const statusItems = [
    {
      label: 'Concluídos',
      value: stats.completed,
      icon: CheckCircle2,
      color: 'text-success',
      bg: 'bg-success/10',
    },
    {
      label: 'Em andamento',
      value: stats.inProgress,
      icon: Clock,
      color: 'text-info',
      bg: 'bg-info/10',
    },
    {
      label: 'Bloqueados',
      value: stats.blockedByClient,
      icon: AlertCircle,
      color: 'text-warning',
      bg: 'bg-warning/10',
    },
    {
      label: 'Atrasados',
      value: stats.overdue,
      icon: XCircle,
      color: 'text-destructive',
      bg: 'bg-destructive/10',
    },
  ];

  return (
    <motion.div
      variants={fadeIn}
      className="bg-card border border-border rounded-card shadow-token-sm p-6"
    >
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-foreground flex items-center gap-2">
          <Calendar className="w-5 h-5 text-primary" />
          Fechamentos Mensais
        </h2>
        <span className="text-sm font-medium text-muted-foreground">
          {month}/{year}
        </span>
      </div>

      {/* Progress Bar */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium text-foreground">
            Progresso geral
          </span>
          <span className="text-2xl font-bold text-foreground">
            {stats.completionPercentage}%
          </span>
        </div>
        <div className="h-3 bg-muted rounded-full overflow-hidden">
          <motion.div
            initial={{ width: 0 }}
            animate={{ width: `${stats.completionPercentage}%` }}
            transition={{ duration: 1, ease: 'easeOut' }}
            className={`h-full ${progressColor} rounded-full`}
          />
        </div>
        <p className="text-xs text-muted-foreground mt-2">
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
              className={`${item.bg} border border-border rounded-lg p-3`}
            >
              <div className="flex items-center gap-2 mb-1">
                <Icon className={`w-4 h-4 ${item.color}`} />
                <span className="text-xs font-medium text-muted-foreground">
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
        <div className="mt-4 p-3 bg-destructive/10 border border-destructive/30 rounded-lg">
          <p className="text-sm font-medium text-destructive">
            {stats.overdue} fechamento{stats.overdue > 1 ? 's' : ''} atrasado
            {stats.overdue > 1 ? 's' : ''} precisa{stats.overdue > 1 ? 'm' : ''}{' '}
            de atenção
          </p>
        </div>
      )}
    </motion.div>
  );
}
