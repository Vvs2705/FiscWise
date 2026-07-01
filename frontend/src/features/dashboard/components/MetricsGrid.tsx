import { motion } from 'framer-motion';
import { Calendar, Users, FileText, Receipt } from 'lucide-react';

interface Metric {
  id: string;
  label: string;
  value: number;
  detail: string;
  icon: 'calendar' | 'users' | 'document' | 'receipt';
}

interface MetricsGridProps {
  metrics: Metric[];
}

const iconMap = {
  calendar: Calendar,
  users: Users,
  document: FileText,
  receipt: Receipt,
};

const itemVariants = {
  hidden: { opacity: 0, y: 18 },
  show: { opacity: 1, y: 0, transition: { duration: 0.45, ease: 'easeOut' as const } },
};

export function MetricsGrid({ metrics }: MetricsGridProps) {
  return (
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
      {metrics.map((metric) => {
        const Icon = iconMap[metric.icon];
        return (
          <motion.div
            key={metric.id}
            variants={itemVariants}
            className="rounded-card border border-border bg-card shadow-token-sm px-5 py-5"
          >
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">{metric.label}</p>
                <p className="mt-3 text-3xl font-semibold tracking-tight text-foreground">
                  {metric.value}
                </p>
                <p className="mt-2 text-sm text-muted-foreground">{metric.detail}</p>
              </div>
              <div className="rounded-card border border-border bg-muted p-3 text-primary">
                <Icon className="h-5 w-5" />
              </div>
            </div>
          </motion.div>
        );
      })}
    </div>
  );
}
