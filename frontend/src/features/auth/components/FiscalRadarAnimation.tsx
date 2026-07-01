import { motion } from 'framer-motion';

const radarItems = [
  {
    id: 'cliente-das',
    label: 'Cliente com DAS pendente',
    tone: 'bg-destructive',
    glow: 'shadow-[0_0_12px_hsl(var(--destructive)/0.45)]',
    position: { top: '26%', left: '68%' },
    delay: 0.2,
  },
  {
    id: 'cliente-docs',
    label: 'Documento aguardando envio',
    tone: 'bg-warning',
    glow: 'shadow-[0_0_12px_hsl(var(--warning)/0.45)]',
    position: { top: '58%', left: '30%' },
    delay: 0.8,
  },
  {
    id: 'cliente-cert',
    label: 'Certificado vence em 12 dias',
    tone: 'bg-success',
    glow: 'shadow-[0_0_12px_hsl(var(--success)/0.45)]',
    position: { top: '38%', left: '44%' },
    delay: 1.4,
  },
];

export function FiscalRadarAnimation() {
  return (
    <div className="relative overflow-hidden rounded-[20px] border border-white/10 bg-card/35 p-4 shadow-token backdrop-blur-xl flex flex-col justify-between"
         style={{ minHeight: 'clamp(180px, 22vh, 290px)' }}>
      
      <style>{`
        @media (max-height: 850px) and (min-width: 1024px) {
          .radar-legend { display: none !important; }
          .radar-circle { max-width: 150px !important; }
          .radar-description { display: none !important; }
        }
      `}</style>

      <div className="relative flex items-center justify-between gap-4">
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-primary/70">
            Radar fiscal
          </p>
          <p className="radar-description mt-0.5 text-xs text-muted-foreground">
            Monitoramento ao vivo da carteira de clientes.
          </p>
        </div>
        <span className="rounded-full border border-success/30 bg-success/10 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.1em] text-success">
          Ao vivo
        </span>
      </div>

      <div className="radar-circle relative mx-auto aspect-square w-full max-w-[210px] mt-2">
        <div className="absolute inset-0 rounded-full border border-primary/15" />
        <div className="absolute inset-[11%] rounded-full border border-primary/15" />
        <div className="absolute inset-[22%] rounded-full border border-primary/15" />
        <div className="absolute inset-[33%] rounded-full border border-primary/15" />
        <div className="absolute inset-1/2 h-px -translate-x-1/2 -translate-y-1/2 bg-primary/15" />
        <div className="absolute left-1/2 top-0 h-full w-px -translate-x-1/2 bg-primary/15" />

        <motion.div
          aria-hidden="true"
          className="absolute inset-[6%] origin-center rounded-full"
          animate={{ rotate: 360 }}
          transition={{ duration: 9, repeat: Infinity, ease: 'linear' }}
          style={{
            background:
              'conic-gradient(from 90deg, transparent 0deg, hsl(var(--primary) / 0.04) 260deg, hsl(var(--primary) / 0.42) 322deg, hsl(var(--info) / 0.08) 360deg)',
            clipPath: 'polygon(50% 50%, 100% 22%, 100% 0%, 0% 0%, 0% 100%)',
          }}
        />

        <motion.div
          className="absolute left-1/2 top-1/2 h-3.5 w-3.5 -translate-x-1/2 -translate-y-1/2 rounded-full border border-primary/60 bg-primary/30 shadow-[0_0_20px_hsl(var(--primary)/0.35)]"
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
            <div className={`h-3 w-3 rounded-full ${item.tone} ${item.glow}`} />
            <div className="pointer-events-none absolute left-1/2 top-[calc(100%+10px)] z-10 w-40 -translate-x-1/2 rounded-xl border border-white/10 bg-card/90 px-3 py-2 text-[11px] text-muted-foreground opacity-0 shadow-token transition-opacity duration-200 group-hover:opacity-100">
              {item.label}
            </div>
          </motion.div>
        ))}
      </div>

      <div className="radar-legend mt-3 grid gap-2 grid-cols-3">
        {radarItems.map((item) => (
          <div
            key={item.id}
            className="rounded-xl border border-white/10 bg-white/5 p-1.5 text-[10px] text-muted-foreground"
          >
            <div className="flex items-center gap-1.5">
              <span className={`h-2 w-2 shrink-0 rounded-full ${item.tone}`} />
              <span className="font-medium text-foreground truncate">{item.label}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
