import { motion } from 'framer-motion';
import {
  AlarmClockCheck,
  BadgeCheck,
  Files,
  ShieldAlert,
} from 'lucide-react';

const metrics = [
  {
    title: 'Hoje',
    value: '7 obrigações',
    description: 'vencendo nesta janela',
    icon: AlarmClockCheck,
    accent: 'from-primary/25 to-success/10',
    border: 'border-primary/20',
  },
  {
    title: 'Documentos',
    value: '12 aguardando',
    description: 'envio dos clientes',
    icon: Files,
    accent: 'from-info/25 to-info/10',
    border: 'border-info/20',
  },
  {
    title: 'Certificados',
    value: '2 vencem',
    description: 'ainda este mês',
    icon: ShieldAlert,
    accent: 'from-warning/25 to-warning/10',
    border: 'border-warning/20',
  },
  {
    title: 'Fechamentos',
    value: '81% concluídos',
    description: 'da carteira ativa',
    icon: BadgeCheck,
    accent: 'from-success/25 to-primary/10',
    border: 'border-success/20',
  },
];

export function FloatingMetricCards() {
  return (
    <div className="grid gap-3 sm:grid-cols-2">
      {metrics.map((metric, index) => (
        <motion.div
          key={metric.title}
          initial={{ opacity: 0, y: 18 }}
          animate={{ opacity: 1, y: [0, -6, 0] }}
          transition={{
            opacity: { duration: 0.4, delay: index * 0.1 },
            y: {
              duration: 5 + index * 0.8,
              repeat: Infinity,
              ease: 'easeInOut',
              delay: index * 0.15,
            },
          }}
          className={`rounded-[20px] border ${metric.border} bg-gradient-to-br ${metric.accent} p-3 shadow-token backdrop-blur-md flex flex-col justify-between`}
          style={{ minHeight: 'clamp(85px, 11vh, 110px)' }}
        >
          <div>
            <div className="mb-2 flex items-center justify-between gap-2">
              <span className="text-[10px] font-semibold uppercase tracking-[0.18em] text-muted-foreground/80">
                {metric.title}
              </span>
              <div className="rounded-xl border border-white/10 bg-white/10 p-1.5">
                <metric.icon className="h-3.5 w-3.5 text-primary" />
              </div>
            </div>
            <p className="text-base font-bold text-white tracking-tight leading-none">{metric.value}</p>
          </div>
          <p className="mt-1.5 text-[11px] text-muted-foreground leading-tight">{metric.description}</p>
        </motion.div>
      ))}
    </div>
  );
}
