import { motion } from 'framer-motion';
import { Calendar, CheckCircle2, Clock, AlertTriangle } from 'lucide-react';
import { staggerContainer, fadeIn } from '../../../lib/motion';

interface TimelineItem {
  id: string;
  title: string;
  type: 'obligation' | 'task' | 'deadline';
  status: 'pending' | 'completed' | 'overdue';
  time?: string;
}

interface DayTimeline {
  day: string;
  date: string;
  isToday: boolean;
  items: TimelineItem[];
}

interface FiscalWeekTimelineProps {
  timeline: DayTimeline[];
  isLoading?: boolean;
}

const statusStyles = {
  pending: 'bg-info/10 text-info border-info/30',
  completed: 'bg-success/10 text-success border-success/30',
  overdue: 'bg-destructive/10 text-destructive border-destructive/30',
};

const statusIcons = {
  pending: Clock,
  completed: CheckCircle2,
  overdue: AlertTriangle,
};

export function FiscalWeekTimeline({ timeline, isLoading }: FiscalWeekTimelineProps) {
  if (isLoading) {
    return (
      <div className="bg-card border border-border rounded-card shadow-token-sm p-6">
        <div className="h-6 w-56 bg-muted animate-pulse rounded mb-4" />
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="space-y-2">
              <div className="h-5 w-32 bg-muted animate-pulse rounded" />
              <div className="h-12 bg-muted animate-pulse rounded-lg" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (timeline.length === 0) {
    return (
      <motion.div
        variants={fadeIn}
        className="bg-card border border-border rounded-card shadow-token-sm p-8 text-center"
      >
        <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-info/10 flex items-center justify-center">
          <Calendar className="w-8 h-8 text-info" />
        </div>
        <h3 className="text-lg font-semibold text-foreground mb-2">
          Nenhuma atividade agendada
        </h3>
        <p className="text-muted-foreground text-sm">
          Sua agenda fiscal está livre para esta semana.
        </p>
      </motion.div>
    );
  }

  return (
    <motion.div
      variants={staggerContainer}
      initial="initial"
      animate="animate"
      className="bg-card border border-border rounded-card shadow-token-sm p-6"
    >
      <h2 className="text-lg font-semibold text-foreground mb-4 flex items-center gap-2">
        <Calendar className="w-5 h-5 text-primary" />
        Agenda Fiscal da Semana
      </h2>

      <div className="space-y-6">
        {timeline.map((day) => (
          <motion.div key={day.date} variants={fadeIn} className="space-y-2">
            <div className="flex items-center gap-2">
              <h3
                className={`font-semibold ${
                  day.isToday ? 'text-primary' : 'text-foreground'
                }`}
              >
                {day.day}
              </h3>
              <span className="text-sm text-muted-foreground">{day.date}</span>
              {day.isToday && (
                <span className="px-2 py-0.5 rounded-full text-xs font-semibold bg-primary/10 text-primary border border-primary/30">
                  Hoje
                </span>
              )}
            </div>

            {day.items.length === 0 ? (
              <div className="bg-muted border border-border rounded-lg p-3 text-sm text-muted-foreground">
                Nenhuma atividade
              </div>
            ) : (
              <div className="space-y-2">
                {day.items.map((item) => {
                  const StatusIcon = statusIcons[item.status];
                  return (
                    <div
                      key={item.id}
                      className="bg-muted border border-border rounded-lg p-3 hover:border-primary/30 transition-all cursor-pointer group"
                    >
                      <div className="flex items-center justify-between gap-3">
                        <div className="flex items-center gap-3 flex-1 min-w-0">
                          <div
                            className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 border ${
                              statusStyles[item.status]
                            }`}
                          >
                            <StatusIcon className="w-4 h-4" />
                          </div>
                          <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium text-foreground truncate">
                              {item.title}
                            </p>
                            {item.time && (
                              <p className="text-xs text-muted-foreground">
                                {item.time}
                              </p>
                            )}
                          </div>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </motion.div>
        ))}
      </div>
    </motion.div>
  );
}
