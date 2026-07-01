import {
  BriefcaseBusiness,
  Clock3,
  ShieldCheck,
} from 'lucide-react';
import { Logo } from '@/components/Logo';
import { FiscalRadarAnimation } from './FiscalRadarAnimation';
import { FloatingMetricCards } from './FloatingMetricCards';

const trustPoints = [
  {
    icon: BriefcaseBusiness,
    title: 'Carteira organizada',
    description: 'Clientes, obrigações e documentos reunidos no mesmo ambiente.',
  },
  {
    icon: Clock3,
    title: 'Rotina mais previsível',
    description: 'Saiba exatamente o que vence hoje e o que ainda depende do cliente.',
  },
  {
    icon: ShieldCheck,
    title: 'Segurança real',
    description: 'Seus clientes e documentos protegidos em um ambiente exclusivo.',
  },
];

export function LoginBrandPanel() {
  return (
    <section
      className="relative border-white/10 text-white hidden lg:flex lg:h-screen lg:max-h-screen lg:overflow-hidden lg:border-r lg:flex-col"
      style={{
        padding: 'clamp(24px, 4vh, 48px) clamp(24px, 4vw, 56px)',
        background:
          'radial-gradient(circle at 14% 18%, hsl(var(--primary) / 0.22), transparent 26%), radial-gradient(circle at 86% 18%, hsl(var(--info) / 0.18), transparent 24%), linear-gradient(135deg, hsl(var(--sidebar)) 0%, hsl(var(--sidebar)) 55%, hsl(var(--sidebar)) 100%)',
      }}
    >
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute left-10 top-10 h-40 w-40 rounded-full bg-primary/10 blur-3xl" />
        <div className="absolute bottom-12 right-0 h-52 w-52 rounded-full bg-success/10 blur-3xl" />
      </div>

      <div className="relative z-10 flex w-full flex-col flex-1 justify-between">
        <div className="flex items-center justify-between gap-4">
          <Logo variant="full" theme="dark" size={38} />
          <div className="hidden rounded-full border border-white/10 bg-white/5 px-4 py-1.5 text-[11px] font-semibold uppercase tracking-[0.22em] text-primary/90 lg:block">
            Fiscal Intelligence OS
          </div>
        </div>

        <div className="mt-5 max-w-xl">
          <span className="inline-flex rounded-full border border-primary/20 bg-primary/10 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.2em] text-primary/90">
            Feito para contador autônomo
          </span>
          <h1 className="mt-3 font-semibold leading-none tracking-tight text-white animate-fade-in-up"
              style={{ fontSize: 'clamp(2.1rem, 3.2vw, 3.2rem)', lineHeight: 1.05, letterSpacing: '-0.04em' }}>
            Controle sua carteira contábil com precisão.
          </h1>
          <p className="mt-3 text-xs leading-relaxed text-muted-foreground sm:text-sm"
             style={{ maxWidth: '600px', fontSize: 'clamp(0.85rem, 1.05vw, 1rem)', lineHeight: 1.5 }}>
            Clientes, documentos, prazos, certificados e obrigações fiscais em uma central feita para quem precisa manter a rotina em dia e saber onde agir primeiro.
          </p>
        </div>

        <div className="mt-4 grid gap-3 grid-cols-3">
          {trustPoints.map((point) => (
            <div
              key={point.title}
              className="rounded-[16px] border border-white/10 bg-white/5 p-3 backdrop-blur-md flex flex-col justify-between"
              style={{ minHeight: 'clamp(100px, 13vh, 130px)' }}
            >
              <div>
                <div className="mb-1.5 flex h-7 w-7 items-center justify-center rounded-lg border border-white/10 bg-white/10">
                  <point.icon className="h-3.5 w-3.5 text-primary" />
                </div>
                <p className="text-[11px] font-bold text-white tracking-tight leading-tight">{point.title}</p>
              </div>
              <p className="mt-1 text-[10px] leading-snug text-muted-foreground/90">{point.description}</p>
            </div>
          ))}
        </div>

        <div className="mt-4">
          <FloatingMetricCards />
        </div>

        <div className="mt-4 flex-1 flex flex-col justify-center">
          <FiscalRadarAnimation />
        </div>

        <div className="mt-3 flex flex-wrap gap-1.5 text-[10px] text-muted-foreground">
          <span className="rounded-full border border-white/10 bg-white/5 px-2.5 py-1">
            Atenção de hoje
          </span>
          <span className="rounded-full border border-white/10 bg-white/5 px-2.5 py-1">
            Obrigações e prazos
          </span>
          <span className="rounded-full border border-white/10 bg-white/5 px-2.5 py-1">
            Documentos sob controle
          </span>
        </div>
      </div>
    </section>
  );
}
