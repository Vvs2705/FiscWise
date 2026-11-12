import { Link } from 'react-router-dom';
import {
  ArrowRight,
  Building2,
  CalendarClock,
  Check,
  FileStack,
  KeyRound,
  LockKeyhole,
  Server,
  ShieldCheck,
  Users,
} from 'lucide-react';
import { ThemeToggle } from '@/components/ThemeToggle';
import { Badge, type BadgeTone } from '@/components/ui/Badge';
import { LoginFooter, LoginLogo } from '@/features/auth/components/LoginShell';
import { cn } from '@/lib/utils';

/*
 * Página inicial pública (contador autônomo e escritório contábil).
 * Trava de honestidade: só o que o README marca como ✅ ou 🟡, com o 🟡
 * descrito como é. Sem preços, depoimentos, números ou métricas.
 * Só CSS (sem framer-motion), conforme SISTEMA_DE_DESIGN.md §7.
 */

const FOCUS_RING =
  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background';

const BTN_BASE = cn(
  'inline-flex select-none items-center justify-center gap-2 whitespace-nowrap rounded-md font-medium',
  'transition-[background-color,border-color,color,transform] duration-100 ease-out active:scale-[0.98]',
  FOCUS_RING,
);
const BTN_PRIMARY = cn(BTN_BASE, 'bg-primary text-primary-foreground shadow-sm hover:bg-primary/90');
const BTN_OUTLINE = cn(
  BTN_BASE,
  'border border-input bg-card text-foreground hover:border-muted-foreground/30 hover:bg-muted',
);
const NAV_LINK = cn(
  'rounded-md px-2 py-2 text-sm font-medium text-muted-foreground transition-colors duration-100 hover:text-foreground',
  FOCUS_RING,
);

const SECTION = 'mx-auto w-full max-w-7xl px-4 sm:px-6 lg:px-10';

/* ─── Conteúdo ─────────────────────────────────────────────────────────── */

const pains = [
  {
    icon: CalendarClock,
    pain: 'Prazo que passa despercebido vira multa para o cliente.',
    answer: 'Calendário de obrigações gerado por regime, CNAE, município e UF, com recorrência e prazos.',
  },
  {
    icon: Users,
    pain: 'Cliente que não manda o documento a tempo.',
    answer: 'Portal do cliente: ele envia documentos e acessa as guias sem depender de e-mail ou WhatsApp.',
  },
  {
    icon: FileStack,
    pain: 'Fechamento do mês espalhado em planilhas.',
    answer: 'Fechamento por competência com dossiê em PDF pronto para entregar.',
  },
  {
    icon: KeyRound,
    pain: 'Certificado digital vencendo sem ninguém ver.',
    answer: 'Cadastro de certificados A1 e A3 com alerta de validade.',
  },
];

const steps = [
  {
    title: 'Cadastre seus clientes',
    description: 'Razão social, CNPJ, regime tributário, CNAE e município de cada empresa da carteira.',
  },
  {
    title: 'O FiscWise monta o calendário de cada um',
    description: 'As obrigações e os prazos saem do perfil fiscal do cliente, com a recorrência de cada uma.',
  },
  {
    title: 'Você e o cliente acompanham tudo no mesmo lugar',
    description: 'O escritório vê prazos, guias e fechamentos; o cliente envia documentos pelo portal.',
  },
];

const available = [
  {
    title: 'Clientes e documentos',
    description: 'Carteira de clientes com upload e organização de documentos.',
  },
  {
    title: 'Obrigações fiscais',
    description: 'Calendário por regime, CNAE, município e UF, com recorrência e prazos.',
  },
  {
    title: 'Fechamento mensal com dossiê PDF',
    description: 'Fechamento por competência e dossiê em PDF gerado pelo sistema.',
  },
  {
    title: 'Portal do cliente',
    description: 'Acesso por convite para o cliente enviar documentos e ver as guias.',
  },
  {
    title: 'Guias com registro e conciliação',
    description:
      'Registro de DAS, DARF, GPS e ISS, conciliação do pagamento e comprovantes. A guia ainda não é gerada automaticamente na Receita.',
  },
  {
    title: 'Certificados com alerta',
    description:
      'Cadastro de certificados A1 e A3 e alerta de validade. Ainda não guarda a chave nem assina documentos.',
  },
  {
    title: 'Honorários e inadimplência',
    description: 'Contas a receber dos honorários e controle de quem está em atraso.',
  },
];

const comingSoon = [
  { title: 'Emissão de NFS-e', description: 'Em homologação com a prefeitura e o Portal Nacional.' },
  { title: 'Consulta e-CAC', description: 'Depende de contrato com o SERPRO.' },
  { title: 'WhatsApp oficial', description: 'Depende da API oficial do WhatsApp Business.' },
];

const trust = [
  { icon: Server, title: 'Dados armazenados em servidores no Brasil' },
  { icon: Building2, title: 'Dados de cada escritório isolados' },
  { icon: LockKeyhole, title: 'Login com verificação em 2 etapas' },
];

const faqs = [
  {
    q: 'Para quem é o FiscWise?',
    a: 'Para o contador autônomo e o escritório contábil que precisam organizar a carteira de clientes: prazos, documentos, guias e o fechamento de cada mês.',
  },
  {
    q: 'O que o FiscWise já faz hoje?',
    a: 'Cadastro de clientes e documentos, calendário de obrigações fiscais, fechamento mensal com dossiê em PDF, portal do cliente, registro e conciliação de guias, alerta de validade de certificados e controle de honorários.',
  },
  {
    q: 'O FiscWise emite nota fiscal?',
    a: 'Ainda não. A emissão de NFS-e está em homologação com a prefeitura e o Portal Nacional. Quando estiver liberada, avisamos aqui.',
  },
];

type ExampleRow = { name: string; detail: string; status: string; tone: BadgeTone };

const exampleRows: ExampleRow[] = [
  { name: 'DAS · vence dia 20', detail: 'Cliente A · Simples Nacional', status: 'A vencer', tone: 'warning' },
  { name: 'DCTFWeb', detail: 'Cliente B · Lucro Presumido', status: 'Entregue', tone: 'success' },
  { name: 'EFD-Reinf', detail: 'Cliente B · Lucro Presumido', status: 'Em andamento', tone: 'info' },
  { name: 'Honorários', detail: 'Cliente C · mensal', status: 'Em aberto', tone: 'neutral' },
];

/* ─── Partes ───────────────────────────────────────────────────────────── */

function TopBar() {
  return (
    <header className="w-full border-b border-border bg-background">
      <div className={cn(SECTION, 'flex h-16 items-center justify-between gap-3')}>
        <Link to="/" aria-label="FiscWise, página inicial" className={cn('shrink-0 rounded-md', FOCUS_RING)}>
          <LoginLogo />
        </Link>

        <nav aria-label="Principal" className="flex min-w-0 items-center gap-1 sm:gap-2">
          <a href="#como-funciona" className={cn(NAV_LINK, 'hidden md:inline-flex')}>
            Como funciona
          </a>
          <a href="/faq/" className={cn(NAV_LINK, 'hidden md:inline-flex')}>
            Perguntas frequentes
          </a>
          <ThemeToggle />
          <Link to="/login" className={NAV_LINK}>
            Entrar
          </Link>
          <Link to="/register" className={cn(BTN_PRIMARY, 'h-10 px-3 text-sm sm:px-4')}>
            <span>
              Criar conta<span className="hidden sm:inline"> grátis</span>
            </span>
          </Link>
        </nav>
      </div>
    </header>
  );
}

function ObligationsIllustration() {
  return (
    <figure
      aria-label="Exemplo ilustrativo de calendário de obrigações"
      className="w-full rounded-lg border border-border bg-card shadow-lg"
    >
      <div className="flex items-center justify-between gap-3 border-b border-border px-4 py-3 sm:px-5">
        <div className="min-w-0">
          <p className="text-sm font-semibold text-foreground">Calendário de obrigações</p>
          <p className="text-xs text-muted-foreground">Competência do mês</p>
        </div>
        <Badge variant="neutral">Exemplo</Badge>
      </div>

      <ul className="divide-y divide-border">
        {exampleRows.map((row) => (
          <li key={row.name} className="flex items-center justify-between gap-3 px-4 py-3 sm:px-5">
            <div className="min-w-0">
              <p className="truncate text-sm font-medium text-foreground">{row.name}</p>
              <p className="truncate text-xs text-muted-foreground">{row.detail}</p>
            </div>
            <Badge variant={row.tone} className="shrink-0">
              {row.status}
            </Badge>
          </li>
        ))}
      </ul>

      <figcaption className="border-t border-border px-4 py-2.5 text-xs text-muted-foreground sm:px-5">
        Ilustração com dados fictícios.
      </figcaption>
    </figure>
  );
}

function SectionHeading({ id, title, description }: { id: string; title: string; description?: string }) {
  return (
    <div className="max-w-2xl">
      <h2 id={id} className="text-2xl font-semibold tracking-tight text-foreground sm:text-3xl">
        {title}
      </h2>
      {description && <p className="mt-3 text-base text-muted-foreground">{description}</p>}
    </div>
  );
}

/* ─── Página ───────────────────────────────────────────────────────────── */

export function LandingPage() {
  return (
    <div className="flex min-h-screen flex-col overflow-x-clip bg-background text-foreground">
      <TopBar />

      <main className="flex-1">
        {/* Hero */}
        <section className={cn(SECTION, 'grid items-center gap-10 py-12 sm:py-16 lg:grid-cols-[minmax(0,1.1fr)_minmax(0,1fr)] lg:gap-16 lg:py-20')}>
          <div className="animate-fade-in-up [animation-duration:200ms]">
            <p className="text-sm font-medium text-primary">Para contadores e escritórios contábeis</p>
            <h1 className="mt-3 text-3xl font-semibold leading-tight tracking-tight text-foreground sm:text-4xl lg:text-5xl">
              Sua carteira de clientes em dia, sem planilha e sem prazo perdido.
            </h1>
            <p className="mt-5 max-w-xl text-base text-muted-foreground sm:text-lg">
              O FiscWise organiza obrigações, documentos, guias e o fechamento do mês de cada cliente em
              um só lugar. Feito para o contador autônomo e o escritório contábil.
            </p>
            <div className="mt-8 flex flex-col gap-3 sm:flex-row">
              <Link to="/register" className={cn(BTN_PRIMARY, 'h-11 px-5 text-base')}>
                Criar conta grátis
                <ArrowRight className="h-4 w-4" aria-hidden="true" />
              </Link>
              <Link to="/login" className={cn(BTN_OUTLINE, 'h-11 px-5 text-base')}>
                Entrar
              </Link>
            </div>
          </div>

          <div className="animate-fade-in-up [animation-delay:40ms] [animation-duration:200ms]">
            <ObligationsIllustration />
          </div>
        </section>

        {/* Dores */}
        <section aria-labelledby="dores-title" className="border-t border-border bg-card/60 py-14 sm:py-20">
          <div className={SECTION}>
            <SectionHeading
              id="dores-title"
              title="Você conhece esta rotina?"
              description="Os problemas de todo mês em um escritório contábil, e o que o FiscWise faz com cada um."
            />
            <ul className="mt-10 grid gap-4 sm:grid-cols-2">
              {pains.map(({ icon: Icon, pain, answer }) => (
                <li key={pain} className="flex flex-col rounded-lg border border-border bg-card p-5">
                  <span className="flex h-9 w-9 items-center justify-center rounded-md bg-accent text-primary">
                    <Icon className="h-5 w-5" aria-hidden="true" />
                  </span>
                  <p className="mt-4 text-base font-semibold text-foreground">{pain}</p>
                  <p className="mt-3 flex gap-2 border-t border-border pt-3 text-sm text-muted-foreground">
                    <ArrowRight className="mt-0.5 h-4 w-4 shrink-0 text-primary" aria-hidden="true" />
                    <span>
                      <span className="sr-only">Como o FiscWise resolve: </span>
                      {answer}
                    </span>
                  </p>
                </li>
              ))}
            </ul>
          </div>
        </section>

        {/* Como funciona */}
        <section
          id="como-funciona"
          aria-labelledby="como-funciona-title"
          className="scroll-mt-4 border-t border-border py-14 sm:py-20"
        >
          <div className={SECTION}>
            <SectionHeading id="como-funciona-title" title="Como funciona" />
            <ol className="mt-10 grid gap-6 md:grid-cols-3">
              {steps.map((step, i) => (
                <li key={step.title} className="flex gap-4 md:flex-col">
                  <span
                    aria-hidden="true"
                    className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full border border-primary/30 bg-accent font-mono text-sm font-medium tabular-nums text-primary"
                  >
                    {i + 1}
                  </span>
                  <div className="min-w-0">
                    <p className="text-base font-semibold text-foreground">
                      <span className="sr-only">Passo {i + 1}: </span>
                      {step.title}
                    </p>
                    <p className="mt-1 text-sm text-muted-foreground">{step.description}</p>
                  </div>
                </li>
              ))}
            </ol>
          </div>
        </section>

        {/* O que já funciona */}
        <section aria-labelledby="funciona-title" className="border-t border-border bg-card/60 py-14 sm:py-20">
          <div className={SECTION}>
            <SectionHeading
              id="funciona-title"
              title="O que já funciona hoje"
              description="Preferimos mostrar o que está pronto e dizer o que ainda falta."
            />
            <ul className="mt-10 grid gap-x-8 gap-y-5 sm:grid-cols-2 lg:grid-cols-3">
              {available.map((item) => (
                <li key={item.title} className="flex gap-3">
                  <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-success/10 text-success">
                    <Check className="h-3.5 w-3.5" aria-hidden="true" />
                  </span>
                  <div className="min-w-0">
                    <p className="text-sm font-semibold text-foreground">{item.title}</p>
                    <p className="mt-0.5 text-sm text-muted-foreground">{item.description}</p>
                  </div>
                </li>
              ))}
            </ul>

            <div className="mt-10 rounded-lg border border-border bg-card p-5">
              <h3 className="text-base font-semibold text-foreground">Em breve</h3>
              <p className="mt-1 text-sm text-muted-foreground">
                Ainda não está disponível. Mostramos aqui para você saber o que vem depois.
              </p>
              <ul className="mt-4 grid gap-4 sm:grid-cols-3">
                {comingSoon.map((item) => (
                  <li key={item.title} className="min-w-0">
                    <p className="flex items-center gap-2 text-sm font-medium text-foreground">
                      <span aria-hidden="true" className="h-1.5 w-1.5 shrink-0 rounded-full bg-muted-foreground" />
                      {item.title}
                    </p>
                    <p className="mt-0.5 pl-3.5 text-sm text-muted-foreground">{item.description}</p>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </section>

        {/* Confiança */}
        <section aria-labelledby="confianca-title" className="border-t border-border py-14 sm:py-16">
          <div className={SECTION}>
            <h2 id="confianca-title" className="sr-only">
              Segurança dos dados
            </h2>
            <ul className="grid gap-4 sm:grid-cols-3">
              {trust.map(({ icon: Icon, title }) => (
                <li key={title} className="flex items-center gap-3 rounded-lg border border-border bg-card p-4">
                  <Icon className="h-5 w-5 shrink-0 text-primary" aria-hidden="true" />
                  <p className="text-sm font-medium text-foreground">{title}</p>
                </li>
              ))}
            </ul>
          </div>
        </section>

        {/* Perguntas rápidas */}
        <section aria-labelledby="perguntas-title" className="border-t border-border bg-card/60 py-14 sm:py-20">
          <div className={SECTION}>
            <SectionHeading id="perguntas-title" title="Perguntas rápidas" />
            <div className="mt-8 max-w-3xl divide-y divide-border rounded-lg border border-border bg-card">
              {faqs.map((f) => (
                <details key={f.q} className="group">
                  <summary
                    className={cn(
                      'flex cursor-pointer list-none items-center justify-between gap-4 rounded-lg px-5 py-4 text-sm font-semibold text-foreground [&::-webkit-details-marker]:hidden',
                      FOCUS_RING,
                    )}
                  >
                    {f.q}
                    <span
                      aria-hidden="true"
                      className="shrink-0 font-mono text-base text-muted-foreground transition-transform duration-150 group-open:rotate-45"
                    >
                      +
                    </span>
                  </summary>
                  <p className="px-5 pb-4 text-sm text-muted-foreground">{f.a}</p>
                </details>
              ))}
            </div>
            <p className="mt-6 text-sm">
              <a
                href="/faq/"
                className={cn('rounded-sm font-medium text-primary underline-offset-4 hover:underline', FOCUS_RING)}
              >
                Ver todas as perguntas frequentes
              </a>
            </p>
          </div>
        </section>

        {/* Chamada final */}
        <section aria-labelledby="cta-title" className="border-t border-border py-14 sm:py-20">
          <div className={cn(SECTION, 'flex flex-col items-start gap-6 md:flex-row md:items-center md:justify-between')}>
            <div className="max-w-xl">
              <h2 id="cta-title" className="text-2xl font-semibold tracking-tight text-foreground sm:text-3xl">
                Organize a carteira antes do próximo vencimento.
              </h2>
              <p className="mt-2 flex items-center gap-2 text-sm text-muted-foreground">
                <ShieldCheck className="h-4 w-4 shrink-0 text-primary" aria-hidden="true" />
                Cadastre o escritório e os primeiros clientes.
              </p>
            </div>
            <Link to="/register" className={cn(BTN_PRIMARY, 'h-11 w-full px-5 text-base sm:w-auto')}>
              Criar conta grátis
              <ArrowRight className="h-4 w-4" aria-hidden="true" />
            </Link>
          </div>
        </section>
      </main>

      <div className="border-t border-border">
        <LoginFooter />
      </div>
    </div>
  );
}

export default LandingPage;
