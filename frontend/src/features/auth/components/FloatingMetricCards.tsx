import { motion } from 'framer-motion';
import {
  AlarmClockCheck,
  BadgeCheck,
  Files,
  ShieldAlert,
} from 'lucide-react';
import { floating } from '@/lib/motion';

const metrics = [
  {
    title: 'Hoje',
    value: '7 obrigacoes',
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
    description: 'ainda este mes',
    icon: ShieldAlert,
    accent: 'from-amber-300/25 to-orange-400/10',
    border: 'border-amber-200/20',
  },
  {
    title: 'Fechamentos',
    value: '81% concluidos',
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
          className={`rounded-[24px] border ${metric.border} bg-gradient-to-br ${metric.accent} px-4 py-4 shadow-[0_20px_45px_rgba(8,15,30,0.28)] backdrop-blur-md`}
        >
          <div className="mb-3 flex items-center justify-between gap-3">
            <span className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-200/80">
              {metric.title}
            </span>
            <div className="rounded-2xl border border-white/10 bg-white/10 p-2">
              <metric.icon className="h-4 w-4 text-cyan-100" />
            </div>
          </div>
          <p className="text-lg font-semibold text-white">{metric.value}</p>
          <p className="mt-1 text-sm text-slate-300">{metric.description}</p>
        </motion.div>
      ))}
    </div>
  );
}
