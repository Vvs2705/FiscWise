import { FileText, KeyRound, Server, ShieldCheck, Users, WifiOff } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { Logo } from '@/components/Logo';
import { cn } from '@/lib/utils';

/* Conteúdo oficial (Frente D — posicionamento). */
const AUDIENCE = 'Para pequenas empresas, MEIs e escritórios contábeis';
const HEADLINE = 'Emita notas fiscais sem complicação, mesmo sem internet.';
const SUBHEADLINE = 'Simples para a sua empresa, organizado para o seu contador.';

const benefits: { icon: LucideIcon; title: string; description: string }[] = [
  {
    icon: FileText,
    title: 'NF-e, NFS-e e NFC-e em poucos cliques',
    description: 'Emita, consulte e cancele sem sair da tela.',
  },
  {
    icon: WifiOff,
    title: 'Funciona sem internet',
    description:
      'Suas notas ficam como pendentes de transmissão e são enviadas quando a conexão volta.',
  },
  {
    icon: Users,
    title: 'Seu contador já dentro',
    description: 'Acesso nativo para o escritório contábil acompanhar tudo em tempo real.',
  },
];

const trustItems: { icon: LucideIcon; label: string }[] = [
  { icon: Server, label: 'Servidores no Brasil' },
  { icon: ShieldCheck, label: 'Conforme a LGPD' },
  { icon: KeyRound, label: 'Login com verificação em 2 etapas' },
];

function TrustLine({ tone }: { tone: 'dark' | 'light' }) {
  return (
    <ul
      aria-label="Segurança"
      className={cn(
        'flex flex-wrap items-center gap-x-4 gap-y-2 text-xs',
        tone === 'dark' ? 'text-sidebar-muted' : 'text-muted-foreground',
      )}
    >
      {trustItems.map(({ icon: Icon, label }) => (
        <li key={label} className="inline-flex items-center gap-1.5">
          <Icon className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
          {label}
        </li>
      ))}
    </ul>
  );
}

/** Coluna navy do login (≥ lg): proposta de valor, benefícios e confiança. */
export function LoginBrandPanel() {
  return (
    <aside className="hidden bg-sidebar text-sidebar-foreground lg:flex lg:min-h-screen lg:flex-col lg:px-12 lg:py-10 xl:px-16">
      <Logo variant="full" theme="dark" size={32} />

      <div className="flex flex-1 flex-col justify-center py-12">
        <div className="max-w-lg animate-fade-in-up">
          <p className="text-sm font-medium text-sidebar-muted">{AUDIENCE}</p>
          <h1 className="mt-3 text-3xl font-semibold leading-tight tracking-tight xl:text-4xl">
            {HEADLINE}
          </h1>
          <p className="mt-4 text-base text-sidebar-muted">{SUBHEADLINE}</p>

          <ul className="mt-10 space-y-6">
            {benefits.map(({ icon: Icon, title, description }) => (
              <li key={title} className="flex items-start gap-4">
                <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-white/10">
                  <Icon className="h-4 w-4" aria-hidden="true" />
                </span>
                <div>
                  <p className="text-sm font-semibold">{title}</p>
                  <p className="mt-1 text-sm text-sidebar-muted">{description}</p>
                </div>
              </li>
            ))}
          </ul>
        </div>
      </div>

      <TrustLine tone="dark" />
    </aside>
  );
}

/** Versão compacta (< lg), exibida abaixo do formulário. */
export function LoginValueSummary() {
  return (
    <section aria-labelledby="login-value-title" className="w-full max-w-md lg:hidden">
      <p className="text-xs font-medium text-muted-foreground">{AUDIENCE}</p>
      <h2
        id="login-value-title"
        className="mt-2 text-xl font-semibold leading-tight tracking-tight text-foreground"
      >
        {HEADLINE}
      </h2>
      <p className="mt-2 text-sm text-muted-foreground">{SUBHEADLINE}</p>

      <ul className="mt-6 space-y-4">
        {benefits.map(({ icon: Icon, title, description }) => (
          <li key={title} className="flex items-start gap-3">
            <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-accent text-primary">
              <Icon className="h-4 w-4" aria-hidden="true" />
            </span>
            <div className="text-sm">
              <p className="font-semibold text-foreground">{title}</p>
              <p className="mt-0.5 text-muted-foreground">{description}</p>
            </div>
          </li>
        ))}
      </ul>

      <div className="mt-6 border-t border-border pt-4">
        <TrustLine tone="light" />
      </div>
    </section>
  );
}
