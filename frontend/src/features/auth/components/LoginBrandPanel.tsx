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
    description: 'Clientes, obrigacoes e documentos reunidos no mesmo ambiente.',
  },
  {
    icon: Clock3,
    title: 'Rotina mais previsivel',
    description: 'Saiba exatamente o que vence hoje e o que ainda depende do cliente.',
  },
  {
    icon: ShieldCheck,
    title: 'Seguranca real',
    description: 'Seus clientes e documentos protegidos em um ambiente exclusivo.',
  },
];

export function LoginBrandPanel() {
  return (
    <section
      className="relative overflow-hidden border-white/10 px-6 py-8 text-white lg:flex lg:min-h-screen lg:w-[54%] lg:max-w-[760px] lg:border-r lg:px-10 lg:py-10"
      style={{
        background:
          'radial-gradient(circle at 14% 18%, rgba(45,212,191,0.22), transparent 26%), radial-gradient(circle at 86% 18%, rgba(56,189,248,0.18), transparent 24%), linear-gradient(135deg, #06111f 0%, #0d2136 55%, #081321 100%)',
      }}
    >
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute left-10 top-10 h-40 w-40 rounded-full bg-cyan-300/10 blur-3xl" />
        <div className="absolute bottom-12 right-0 h-52 w-52 rounded-full bg-emerald-400/10 blur-3xl" />
      </div>

      <div className="relative z-10 flex w-full flex-col">
        <div className="flex items-center justify-between gap-4">
          <Logo variant="full" theme="dark" size={38} />
          <div className="hidden rounded-full border border-white/10 bg-white/5 px-4 py-1.5 text-[11px] font-semibold uppercase tracking-[0.22em] text-cyan-100/90 lg:block">
            Fiscal Intelligence OS
          </div>
        </div>

        <div className="mt-10 max-w-xl">
          <span className="inline-flex rounded-full border border-cyan-300/20 bg-cyan-300/10 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.2em] text-cyan-100/90">
            Feito para contador autonomo
          </span>
          <h1 className="mt-5 text-4xl font-semibold leading-tight tracking-[-0.03em] text-white sm:text-5xl">
            Controle sua carteira contabil com precisao.
          </h1>
          <p className="mt-4 max-w-lg text-base leading-7 text-slate-300 sm:text-lg">
            Clientes, documentos, prazos, certificados e obrigacoes fiscais em uma central feita para quem precisa manter a rotina em dia e saber onde agir primeiro.
          </p>
        </div>

        <div className="mt-8 grid gap-3 sm:grid-cols-3">
          {trustPoints.map((point) => (
            <div
              key={point.title}
              className="rounded-[24px] border border-white/10 bg-white/5 px-4 py-4 backdrop-blur-md"
            >
              <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-2xl border border-white/10 bg-white/10">
                <point.icon className="h-5 w-5 text-cyan-100" />
              </div>
              <p className="text-sm font-semibold text-white">{point.title}</p>
              <p className="mt-1 text-sm leading-6 text-slate-300">{point.description}</p>
            </div>
          ))}
        </div>

        <div className="mt-8">
          <FloatingMetricCards />
        </div>

        <div className="mt-8 flex-1">
          <FiscalRadarAnimation />
        </div>

        <div className="mt-6 flex flex-wrap gap-2 text-xs text-slate-300">
          <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1.5">
            Atencao de hoje
          </span>
          <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1.5">
            Obrigações e prazos
          </span>
          <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1.5">
            Documentos sob controle
          </span>
        </div>
      </div>
    </section>
  );
}
