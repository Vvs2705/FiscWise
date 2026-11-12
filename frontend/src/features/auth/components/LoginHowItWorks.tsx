import { Server, Users } from 'lucide-react';
import { Badge } from '@/components/ui/Badge';
import { cn } from '@/lib/utils';

/* Conteúdo oficial (Frente D — posicionamento). Sem números inventados. */
const AUDIENCE = 'Para pequenas empresas, MEIs e escritórios contábeis';
const HEADLINE = 'Emita notas fiscais sem complicação, mesmo sem internet.';

type Step = {
  title: string;
  description: string;
  status?: { label: string; tone: 'warning' | 'success' };
};

const steps: Step[] = [
  {
    title: 'Emita a nota',
    description: 'NF-e, NFS-e e NFC-e em poucos cliques.',
  },
  {
    title: 'Sem internet? Ela entra na fila',
    description: 'A nota fica salva como pendente de transmissão.',
    status: { label: 'Pendente de transmissão', tone: 'warning' },
  },
  {
    title: 'A conexão voltou, enviamos',
    description: 'Transmitimos para a SEFAZ e avisamos você.',
    status: { label: 'Enviada à SEFAZ', tone: 'success' },
  },
];

/**
 * Painel "Como funciona" do login.
 * ≥ lg: coluna da direita, ocupando a altura útil.
 * < lg: versão compacta abaixo do formulário (sem o rodapé de confiança
 * duplicado e com tipografia menor).
 */
export function LoginHowItWorks({ className }: { className?: string }) {
  return (
    <aside
      aria-labelledby="login-how-title"
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
          id="login-how-title"
          className="mt-2 max-w-2xl text-xl font-semibold leading-tight tracking-tight lg:mt-3 lg:text-3xl 2xl:text-4xl"
        >
          {HEADLINE}
        </h2>
      </div>

      <section aria-labelledby="login-steps-title" className="mt-6 lg:mt-8">
        <h3 id="login-steps-title" className="text-sm font-semibold text-foreground">
          Como funciona
        </h3>

        <ol className="mt-4">
          {steps.map((step, i) => {
            const last = i === steps.length - 1;
            return (
              <li key={step.title} className="relative flex gap-4 pb-5 last:pb-0 lg:pb-6">
                {!last && (
                  <span
                    aria-hidden="true"
                    className="absolute bottom-0 left-4 top-8 w-px -translate-x-1/2 bg-primary/25"
                  />
                )}
                <span
                  aria-hidden="true"
                  className="relative flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-primary/30 bg-card font-mono text-xs font-medium tabular-nums text-primary"
                >
                  {String(i + 1).padStart(2, '0')}
                </span>
                <div className="min-w-0 pt-1">
                  <p className="text-sm font-semibold text-foreground">
                    <span className="sr-only">Passo {i + 1}: </span>
                    {step.title}
                  </p>
                  <p className="mt-0.5 text-sm text-muted-foreground">{step.description}</p>
                  {step.status && (
                    <Badge variant={step.status.tone} className="mt-2">
                      <span
                        aria-hidden="true"
                        className={cn(
                          'h-1.5 w-1.5 rounded-full',
                          step.status.tone === 'warning' ? 'bg-warning' : 'bg-success',
                        )}
                      />
                      {step.status.label}
                    </Badge>
                  )}
                </div>
              </li>
            );
          })}
        </ol>
      </section>

      <div className="mt-6 flex flex-col gap-3 border-t border-primary/15 pt-4 sm:flex-row sm:items-center sm:justify-between lg:mt-8 lg:pt-5">
        <p className="flex min-w-0 items-start gap-2 text-sm text-muted-foreground">
          <Users className="mt-0.5 h-4 w-4 shrink-0 text-primary" aria-hidden="true" />
          Seu contador acompanha tudo pelo mesmo sistema.
        </p>
        <p className="inline-flex w-fit shrink-0 items-center gap-1.5 whitespace-nowrap rounded-sm border border-border bg-card px-2 py-1 text-xs font-medium text-foreground">
          <Server className="h-3.5 w-3.5 shrink-0 text-muted-foreground" aria-hidden="true" />
          Dados em servidores no Brasil
        </p>
      </div>
    </aside>
  );
}
