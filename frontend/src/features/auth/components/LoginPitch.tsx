import { Link } from 'react-router-dom';
import { ArrowRight, CalendarClock, FileStack, Server, Users, type LucideIcon } from 'lucide-react';
import { cn } from '@/lib/utils';

/*
 * Painel de posicionamento do login (direita em ≥ lg, compacto abaixo do
 * formulário em < lg). Só o que funciona hoje (README: ✅/🟡). Sem números
 * inventados, sem promessas de emissão de nota.
 */
const AUDIENCE = 'Para contadores e escritórios contábeis';
const HEADLINE = 'A central do contador: prazos, documentos e fechamento em um só lugar.';

type Item = { icon: LucideIcon; title: string; description: string };

const items: Item[] = [
  {
    icon: CalendarClock,
    title: 'Obrigações',
    description: 'Calendário de cada cliente por regime, CNAE, município e UF, com prazos.',
  },
  {
    icon: Users,
    title: 'Portal do cliente',
    description: 'O cliente envia documentos e acessa as guias sem depender de e-mail.',
  },
  {
    icon: FileStack,
    title: 'Fechamento com dossiê PDF',
    description: 'Fechamento por competência e dossiê em PDF pronto para entregar.',
  },
];

const FOCUS_RING =
  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background';

export function LoginPitch({ className }: { className?: string }) {
  return (
    <aside
      aria-labelledby="login-pitch-title"
      className={cn(
        'flex flex-col rounded-lg border border-primary/15 bg-accent/50 p-5 text-foreground sm:p-6',
        'animate-fade-in-up [animation-delay:40ms] [animation-duration:200ms]',
        'lg:justify-between lg:p-8 xl:p-10',
        className,
      )}
    >
      <div>
        <p className="text-xs font-medium text-muted-foreground lg:text-sm">{AUDIENCE}</p>
        <h2
          id="login-pitch-title"
          className="mt-2 max-w-2xl text-xl font-semibold leading-tight tracking-tight lg:mt-3 lg:text-3xl 2xl:text-4xl"
        >
          {HEADLINE}
        </h2>

        <ul className="mt-6 space-y-4 lg:mt-10 lg:space-y-5">
          {items.map(({ icon: Icon, title, description }) => (
            <li key={title} className="flex gap-3">
              <span
                aria-hidden="true"
                className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md border border-primary/30 bg-card text-primary"
              >
                <Icon className="h-4 w-4" />
              </span>
              <div className="min-w-0 pt-0.5">
                <p className="text-sm font-semibold text-foreground">{title}</p>
                <p className="mt-0.5 text-sm text-muted-foreground">{description}</p>
              </div>
            </li>
          ))}
        </ul>
      </div>

      <div className="mt-6 flex flex-col gap-3 border-t border-primary/15 pt-4 sm:flex-row sm:items-center sm:justify-between lg:mt-8 lg:pt-5">
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
    </aside>
  );
}
