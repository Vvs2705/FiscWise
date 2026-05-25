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
    accent: 'from-cyan-400/25 to-emerald-400/10',
    border: 'border-cyan-300/20',
  },
  {
    title: 'Documentos',
    value: '12 aguardando',
    description: 'envio dos clientes',
    icon: Files,
    accent: 'from-blue-400/25 to-sky-400/10',
    border: 'border-sky-300/20',
  },
  {
    title: 'Certificados',
    value: '2 vencem',
    description: 'ainda este mês',
    icon: ShieldAlert,
    accent: 'from-amber-300/25 to-orange-400/10',
    border: 'border-amber-200/20',
  },
  {
    title: 'Fechamentos',
    value: '81% concluídos',
    description: 'da carteira ativa',
    icon: BadgeCheck,
    accent: 'from-emerald-300/25 to-teal-300/10',
    border: 'border-emerald-200/20',
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
          className={`rounded-[20px] border ${metric.border} bg-gradient-to-br ${metric.accent} p-3 shadow-[0_15px_35px_rgba(8,15,30,0.25)] backdrop-blur-md flex flex-col justify-between`}
          style={{ minHeight: 'clamp(85px, 11vh, 110px)' }}
        >
          <div>
            <div className="mb-2 flex items-center justify-between gap-2">
              <span className="text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-200/80">
                {metric.title}
              </span>
              <div className="rounded-xl border border-white/10 bg-white/10 p-1.5">
                <metric.icon className="h-3.5 w-3.5 text-cyan-100" />
              </div>
            </div>
            <p className="text-base font-bold text-white tracking-tight leading-none">{metric.value}</p>
          </div>
          <p className="mt-1.5 text-[11px] text-slate-300 leading-tight">{metric.description}</p>
        </motion.div>
      ))}
    </div>
  );
}
