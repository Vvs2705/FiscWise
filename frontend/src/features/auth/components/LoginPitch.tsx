import { Link } from 'react-router-dom';
import { ArrowRight, CalendarClock, FileStack, Server, Users, WifiOff, type LucideIcon } from 'lucide-react';
import { cn } from '@/lib/utils';

/*
 * Lado de "prova do produto" do login (direita em ≥ lg, abaixo do formulário
 * em < lg): um recorte ilustrativo da tela Hoje do app, com entrada em cascata
 * só em CSS (opacity/transform, ver `.proof-*` em index.css; reduced-motion
 * respeitado). Os números do recorte são EXEMPLO e vêm rotulados como tal.
 * O restante só cita o que funciona hoje (README: ✅/🟡).
 */
const AUDIENCE = 'Para contadores e escritórios contábeis';
const HEADLINE = 'A central do contador: prazos, documentos e fechamento em um só lugar.';

type Feature = { icon: LucideIcon; title: string; description: string };

const features: Feature[] = [
  { icon: CalendarClock, title: 'Obrigações por cliente', description: 'Calendário por regime, CNAE, município e UF.' },
  { icon: Users, title: 'Portal do cliente', description: 'Documentos e guias sem depender de e-mail.' },
  { icon: FileStack, title: 'Fechamento com dossiê PDF', description: 'Por competência, pronto para entregar.' },
  { icon: WifiOff, title: 'Funciona sem internet', description: 'Instale no PC ou celular; sincroniza quando a rede volta.' },
];

const FOCUS_RING =
  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background';

/** Atraso de cascata de cada bloco (60 ms por passo). */
const step = (i: number) => ({ '--i': i }) as React.CSSProperties;

type Tone = 'warning' | 'destructive';
const TONE: Record<Tone, string> = {
  warning: 'border-warning/25 bg-warning/10 text-warning',
  destructive: 'border-destructive/25 bg-destructive/10 text-destructive',
};

function ProofRow({ i, tone, chip, title, detail }: { i: number; tone: Tone; chip: string; title: string; detail: string }) {
  return (
    <li className="proof-enter flex items-start gap-3 px-4 py-3" style={step(i)}>
      <span className={cn('mt-0.5 inline-flex h-6 shrink-0 items-center rounded-sm border px-2 text-xs font-medium', TONE[tone])}>
        {chip}
      </span>
      <div className="min-w-0">
        <p className="text-sm font-medium text-foreground">{title}</p>
        <p className="mt-0.5 text-xs text-muted-foreground">{detail}</p>
      </div>
    </li>
  );
}

export function LoginPitch({ className }: { className?: string }) {
  return (
    <aside
      aria-labelledby="login-pitch-title"
      className={cn(
        'flex flex-col justify-center border-t border-border bg-accent/40 px-4 py-10 text-foreground',
        'sm:px-6 lg:border-l lg:border-t-0 lg:px-12 lg:py-12 xl:px-20',
        className,
      )}
    >
      <div className="mx-auto w-full max-w-[520px]">
        <p className="proof-enter text-sm font-medium text-muted-foreground" style={step(0)}>
          {AUDIENCE}
        </p>
        <h2
          id="login-pitch-title"
          className="proof-enter mt-2 text-xl font-semibold leading-tight tracking-tight lg:text-2xl xl:text-3xl"
          style={step(1)}
        >
          {HEADLINE}
        </h2>

        {/* Recorte da tela Hoje (exemplo ilustrativo) */}
        <figure className="proof-enter mt-8" style={step(2)}>
          <div className="overflow-hidden rounded-lg border border-border bg-card shadow-md">
            <div className="flex items-center justify-between gap-3 border-b border-border px-4 py-3">
              <p className="text-sm font-semibold text-foreground">Hoje</p>
              <p className="font-mono text-xs tabular-nums text-muted-foreground">
                3 obrigações · 1 nota
              </p>
            </div>

            <ul className="divide-y divide-border">
              <ProofRow
                i={3}
                tone="warning"
                chip="Vence hoje"
                title="3 obrigações vencendo"
                detail="DAS, DCTFWeb e EFD-Contribuições de 2 clientes"
              />
              <ProofRow
                i={4}
                tone="destructive"
                chip="Divergência"
                title="1 nota com divergência"
                detail="O valor da nota não confere com o XML recebido"
              />
            </ul>

            <div className="proof-enter border-t border-border bg-muted/50 px-4 py-3" style={step(5)}>
              <div className="flex items-baseline justify-between gap-3 text-xs">
                <span className="font-medium text-foreground">Fechamento do mês</span>
                <span className="font-mono tabular-nums text-muted-foreground">38 de 52 clientes</span>
              </div>
              <div
                className="mt-2 h-1.5 overflow-hidden rounded-full bg-border"
                role="presentation"
              >
                <div
                  className="proof-fill h-full w-full origin-left rounded-full bg-primary"
                  style={{ '--p': 0.73, '--i': 6 } as React.CSSProperties}
                />
              </div>
            </div>
          </div>
          <figcaption className="mt-2 text-xs text-muted-foreground">
            Exemplo ilustrativo da tela Hoje, com dados fictícios.
          </figcaption>
        </figure>

        <ul className="mt-8 grid gap-x-6 gap-y-4 sm:grid-cols-2">
          {features.map(({ icon: Icon, title, description }, idx) => (
            <li key={title} className="proof-enter flex gap-3" style={step(7 + Math.min(idx, 3))}>
              <Icon className="mt-0.5 h-4 w-4 shrink-0 text-primary" aria-hidden="true" />
              <div className="min-w-0">
                <p className="text-sm font-semibold text-foreground">{title}</p>
                <p className="mt-0.5 text-xs text-muted-foreground">{description}</p>
              </div>
            </li>
          ))}
        </ul>

        <div className="mt-8 flex flex-col gap-3 border-t border-border pt-4 sm:flex-row sm:items-center sm:justify-between">
          <Link
            to="/"
            className={cn(
              'inline-flex w-fit items-center gap-1.5 rounded-sm text-sm font-medium text-primary underline-offset-4 hover:underline',
              FOCUS_RING,
            )}
          >
            Conheça o FiscWise
            <ArrowRight className="h-4 w-4" aria-hidden="true" />
          </Link>
          <p className="inline-flex w-fit shrink-0 items-center gap-1.5 whitespace-nowrap rounded-sm border border-border bg-card px-2 py-1 text-xs font-medium text-foreground">
            <Server className="h-3.5 w-3.5 shrink-0 text-muted-foreground" aria-hidden="true" />
            Dados em servidores no Brasil
          </p>
        </div>
      </div>
    </aside>
  );
}
