import { motion } from 'framer-motion';

const radarItems = [
  {
    id: 'cliente-das',
    label: 'Cliente com DAS pendente',
    tone: 'bg-rose-400',
    glow: 'shadow-[0_0_16px_rgba(251,113,133,0.45)]',
    position: { top: '26%', left: '68%' },
    delay: 0.2,
  },
  {
    id: 'cliente-docs',
    label: 'Documento aguardando envio',
    tone: 'bg-amber-300',
    glow: 'shadow-[0_0_16px_rgba(252,211,77,0.45)]',
    position: { top: '58%', left: '30%' },
    delay: 0.8,
  },
  {
    id: 'cliente-cert',
    label: 'Certificado vence em 12 dias',
    tone: 'bg-emerald-300',
    glow: 'shadow-[0_0_16px_rgba(110,231,183,0.45)]',
    position: { top: '38%', left: '44%' },
    delay: 1.4,
  },
];

export function FiscalRadarAnimation() {
  return (
    <div className="relative overflow-hidden rounded-[28px] border border-white/10 bg-slate-950/35 p-6 shadow-[0_24px_80px_rgba(2,8,23,0.45)] backdrop-blur-xl">
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 opacity-70"
        style={{
          backgroundImage:
            'linear-gradient(rgba(148,163,184,0.08) 1px, transparent 1px), linear-gradient(90deg, rgba(148,163,184,0.08) 1px, transparent 1px)',
          backgroundSize: '36px 36px',
        }}
      />

      <div className="relative mb-4 flex items-center justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-cyan-200/70">
            Radar fiscal
          </p>
          <p className="mt-1 text-sm text-slate-300">
            Monitoramento visual da sua carteira e das pendencias do dia.
          </p>
        </div>
        <span className="rounded-full border border-emerald-400/30 bg-emerald-400/10 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] text-emerald-200">
          Ao vivo
        </span>
      </div>

      <div className="relative mx-auto aspect-square w-full max-w-[320px]">
        <div className="absolute inset-0 rounded-full border border-cyan-300/15" />
        <div className="absolute inset-[11%] rounded-full border border-cyan-300/15" />
        <div className="absolute inset-[22%] rounded-full border border-cyan-300/15" />
        <div className="absolute inset-[33%] rounded-full border border-cyan-300/15" />
        <div className="absolute inset-1/2 h-px -translate-x-1/2 -translate-y-1/2 bg-cyan-200/15" />
        <div className="absolute left-1/2 top-0 h-full w-px -translate-x-1/2 bg-cyan-200/15" />

        <motion.div
          aria-hidden="true"
          className="absolute inset-[6%] origin-center rounded-full"
          animate={{ rotate: 360 }}
          transition={{ duration: 9, repeat: Infinity, ease: 'linear' }}
          style={{
            background:
              'conic-gradient(from 90deg, transparent 0deg, rgba(45,212,191,0.04) 260deg, rgba(45,212,191,0.42) 322deg, rgba(56,189,248,0.08) 360deg)',
            clipPath: 'polygon(50% 50%, 100% 22%, 100% 0%, 0% 0%, 0% 100%)',
          }}
        />

        <motion.div
          className="absolute left-1/2 top-1/2 h-4 w-4 -translate-x-1/2 -translate-y-1/2 rounded-full border border-cyan-200/60 bg-cyan-300/30 shadow-[0_0_24px_rgba(45,212,191,0.35)]"
          animate={{ scale: [1, 1.15, 1] }}
          transition={{ duration: 2.4, repeat: Infinity, ease: 'easeInOut' }}
        />

        {radarItems.map((item) => (
          <motion.div
            key={item.id}
            className="group absolute"
            style={item.position}
            initial={{ opacity: 0, scale: 0.7 }}
            animate={{ opacity: [0.55, 1, 0.65], scale: [0.94, 1.08, 1] }}
            transition={{
              duration: 2.6,
              repeat: Infinity,
              repeatType: 'mirror',
              ease: 'easeInOut',
              delay: item.delay,
            }}
          >
            <div className={`h-3.5 w-3.5 rounded-full ${item.tone} ${item.glow}`} />
            <div className="pointer-events-none absolute left-1/2 top-[calc(100%+10px)] z-10 w-40 -translate-x-1/2 rounded-xl border border-white/10 bg-slate-950/90 px-3 py-2 text-[11px] text-slate-200 opacity-0 shadow-xl transition-opacity duration-200 group-hover:opacity-100">
              {item.label}
            </div>
          </motion.div>
        ))}
      </div>

      <div className="mt-5 grid gap-2 sm:grid-cols-3">
        {radarItems.map((item) => (
          <div
            key={item.id}
            className="rounded-2xl border border-white/10 bg-white/5 px-3 py-2 text-xs text-slate-300"
          >
            <div className="mb-2 flex items-center gap-2">
              <span className={`h-2.5 w-2.5 rounded-full ${item.tone}`} />
              <span className="font-medium text-slate-100">{item.label}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
