import { Link } from 'react-router-dom';
import {
  ArrowRight,
  Building2,
  CalendarClock,
  Check,
  CloudUpload,
  Download,
  FileStack,
  KeyRound,
  LockKeyhole,
  Server,
  ShieldCheck,
  Users,
  WifiOff,
} from 'lucide-react';
import { InstallAppButton } from '@/components/InstallAppButton';
import { ThemeToggle } from '@/components/ThemeToggle';
import { Badge, type BadgeTone } from '@/components/ui/Badge';
import { LoginFooter, LoginLogo } from '@/features/auth/components/LoginShell';
import { cn } from '@/lib/utils';
import { useAvailablePlans, type Plan } from '@/lib/hooks/useSubscription';
import { formatPlanPrice, planDescription, planFeatureList, sortPlans } from '@/features/subscription/planFeatures';
import { useAuthStore } from '@/stores/authStore';

/*
 * Página inicial pública (contador autônomo e escritório contábil).
 * Trava de honestidade: só o que o README marca como ✅ ou 🟡, com o 🟡
 * descrito como é. Sem depoimentos, números ou métricas. Preços só os do
 * catálogo do servidor (/subscription/plans), nunca fixos aqui.
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

const offlinePoints = [
  {
    icon: WifiOff,
    title: 'Continua trabalhando quando a rede cai',
    description:
      'Cadastro de clientes, prazos e obrigações, certificados e honorários seguem funcionando sem internet. O que você faz fica guardado no próprio aparelho.',
  },
  {
    icon: CloudUpload,
    title: 'Sincroniza sozinho quando a conexão volta',
    description:
      'Cada alteração entra numa fila e sobe para a nuvem assim que a internet volta, sem duplicar nada. Se algo não puder ser salvo, você vê o motivo.',
  },
  {
    icon: Download,
    title: 'Instale no computador e no celular',
    description:
      'O FiscWise vira um aplicativo na sua área de trabalho pelo Chrome ou pelo Edge, e na tela inicial do celular. Abre em janela própria, sem barra de endereço.',
  },
];

const installSteps = [
  {
    title: 'No computador (Chrome ou Edge)',
    description: 'Clique em “Instalar aplicativo” acima, ou no ícone de instalar no fim da barra de endereço.',
  },
  {
    title: 'No Android',
    description: 'Abra o menu ⋮ do navegador e toque em “Instalar app” ou “Adicionar à tela inicial”.',
  },
  {
    title: 'No iPhone ou iPad (Safari)',
    description: 'Toque em Compartilhar e depois em “Adicionar à Tela de Início”.',
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
  {
    title: 'Funciona sem internet',
    description:
      'Aplicativo instalável no computador e no celular. Clientes, prazos, certificados e honorários podem ser editados offline e sincronizam quando a rede volta.',
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
    q: 'Como assino e como cancelo?',
    a: 'Para assinar, clique em "Assinar" no plano que você quer, na seção Planos e preços. O pagamento é feito no Mercado Pago, por Pix ou cartão. Para cancelar, entre no sistema e clique em "Plano e assinatura" e depois em "Cancelar assinatura". Não tem multa, e o acesso continua até o fim do período já pago.',
  },
  {
    q: 'O FiscWise funciona sem internet?',
    a: 'Sim. Depois do primeiro acesso no aparelho, você continua cadastrando clientes, prazos, certificados e honorários mesmo sem conexão, e consulta as outras telas com os últimos dados carregados. Tudo fica guardado no aparelho e sobe para a nuvem quando a internet volta. O que depende de órgão público ou de arquivo na nuvem, como consulta à Receita, envio e download de documentos e geração do dossiê em PDF, espera a conexão.',
  },
  {
    q: 'Preciso instalar alguma coisa?',
    a: 'Não é obrigatório: o FiscWise abre no navegador. Se preferir, instale como aplicativo no computador pelo Chrome ou pelo Edge, ou no celular pela opção “Adicionar à tela inicial”. Não há arquivo para baixar nem configuração.',
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
          <a href="#offline" className={cn(NAV_LINK, 'hidden lg:inline-flex')}>
            Funciona offline
          </a>
          {/* No celular o botão "Ver planos e preços" do topo da página faz esse papel. */}
          <a href="#planos" className={cn(NAV_LINK, 'hidden sm:inline-flex')}>
            Planos e preços
          </a>
          <a href="/faq/" className={cn(NAV_LINK, 'hidden md:inline-flex')}>
            Perguntas frequentes
          </a>
          <InstallAppButton
            label="Instalar app"
            className="hidden h-10 border border-primary/40 bg-card px-3 text-sm text-primary hover:bg-accent md:inline-flex"
          />
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

type SyncRow = { name: string; detail: string; status: string; tone: BadgeTone };

const syncRows: SyncRow[] = [
  { name: 'Novo cliente cadastrado', detail: 'Cliente D · Simples Nacional', status: 'Na fila', tone: 'warning' },
  { name: 'DAS marcado como pago', detail: 'Cliente A · competência do mês', status: 'Na fila', tone: 'warning' },
  { name: 'Honorário recebido', detail: 'Cliente C · mensal', status: 'Na fila', tone: 'warning' },
];

function OfflineIllustration() {
  return (
    <figure
      aria-label="Exemplo ilustrativo de alterações feitas sem internet aguardando sincronização"
      className="w-full rounded-lg border border-border bg-card shadow-lg"
    >
      <div className="flex items-center justify-between gap-3 border-b border-border px-4 py-3 sm:px-5">
        <p className="inline-flex items-center gap-2 text-sm font-semibold text-foreground">
          <WifiOff className="h-4 w-4 shrink-0 text-primary" aria-hidden="true" />
          Sem internet · 3 pendentes
        </p>
        <Badge variant="neutral">Exemplo</Badge>
      </div>

      <ul className="divide-y divide-border">
        {syncRows.map((row) => (
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

      <p className="flex items-center gap-2 border-t border-border px-4 py-3 text-sm text-foreground sm:px-5">
        <CloudUpload className="h-4 w-4 shrink-0 text-success" aria-hidden="true" />
        A internet voltou: tudo enviado para a nuvem.
      </p>
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

function PlanCard({ plan, isAuthenticated }: { plan: Plan; isAuthenticated: boolean }) {
  const price = plan.price_monthly === null ? null : Number(plan.price_monthly);
  const isFree = price === 0;
  const isCustom = price === null;
  const signupHref = isAuthenticated
    ? isFree
      ? '/painel'
      : `/assinatura?plano=${encodeURIComponent(plan.slug)}`
    : isFree
    ? '/register'
    : `/register?plano=${encodeURIComponent(plan.slug)}`;
  const pixRow = plan.tabela_precos?.find((l) => l.ciclo === 'anual');

  return (
    <li className="flex flex-col rounded-lg border border-border bg-card p-6">
      <h3 className="text-lg font-semibold text-foreground">{plan.name}</h3>
      <p className="mt-2 text-3xl font-semibold tracking-tight text-foreground">
        {isCustom ? 'Sob consulta' : formatPlanPrice(price)}
      </p>
      {pixRow && pixRow.desconto_pix_pct > 0 && (
        <p className="mt-1 text-sm text-muted-foreground">
          ou {pixRow.pix_total.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })} por ano no Pix
          ({pixRow.desconto_pix_pct}% de desconto)
        </p>
      )}
      {planDescription(plan) && <p className="mt-3 text-sm text-muted-foreground">{planDescription(plan)}</p>}
      <ul className="mt-5 flex-1 space-y-2">
        {planFeatureList(plan).map((f) => (
          <li key={f} className="flex items-start gap-2 text-sm text-foreground">
            <Check className="mt-0.5 h-4 w-4 shrink-0 text-success" aria-hidden="true" />
            {f}
          </li>
        ))}
      </ul>
      {isCustom ? (
        <a
          href="mailto:contato@vstack-solutions.com.br?subject=Plano%20Enterprise%20FiscWise"
          className={cn(BTN_OUTLINE, 'mt-6 h-12 w-full px-5 text-base')}
        >
          Falar com a equipe
        </a>
      ) : (
        <Link
          to={signupHref}
          className={cn(isFree ? BTN_OUTLINE : BTN_PRIMARY, 'mt-6 h-12 w-full px-5 text-base')}
        >
          {isFree ? 'Começar grátis' : `Assinar ${plan.name}`}
          {!isFree && <ArrowRight className="h-4 w-4" aria-hidden="true" />}
        </Link>
      )}
    </li>
  );
}

function PricingSection() {
  const { data: plans, isLoading, isError } = useAvailablePlans();
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const visible = sortPlans(plans ?? []);

  return (
    <section id="planos" aria-labelledby="planos-title" className="scroll-mt-4 border-t border-border py-14 sm:py-20">
      <div className={SECTION}>
        <SectionHeading
          id="planos-title"
          title="Planos e preços"
          description="Comece grátis. Assine quando quiser e cancele quando quiser, sem multa, direto no sistema."
        />

        {visible.length > 0 ? (
          <ul className={cn('mt-10 grid gap-4 sm:grid-cols-2', visible.length >= 4 ? 'lg:grid-cols-4' : 'lg:grid-cols-3')}>
            {visible.map((plan) => (
              <PlanCard key={plan.slug} plan={plan} isAuthenticated={isAuthenticated} />
            ))}
          </ul>
        ) : (
          <div className="mt-10 rounded-lg border border-border bg-card p-6 text-sm text-muted-foreground">
            {isLoading && !isError
              ? 'Carregando os planos...'
              : 'Não conseguimos carregar os preços agora. Crie sua conta grátis e veja os planos dentro do sistema.'}
            <div className="mt-4">
              <Link to="/register" className={cn(BTN_PRIMARY, 'h-11 px-5 text-base')}>
                Criar conta grátis
              </Link>
            </div>
          </div>
        )}

        <ul className="mt-8 grid gap-3 text-sm text-muted-foreground sm:grid-cols-3">
          <li className="flex gap-2">
            <Check className="mt-0.5 h-4 w-4 shrink-0 text-primary" aria-hidden="true" />
            Pix com 15% de desconto nos planos trimestral, semestral e anual.
          </li>
          <li className="flex gap-2">
            <Check className="mt-0.5 h-4 w-4 shrink-0 text-primary" aria-hidden="true" />
            Cartão em até 6x sem juros. Pagamento seguro pelo Mercado Pago.
          </li>
          <li className="flex gap-2">
            <Check className="mt-0.5 h-4 w-4 shrink-0 text-primary" aria-hidden="true" />
            Para cancelar: Plano e assinatura, depois Cancelar assinatura. Sem multa.
          </li>
        </ul>
      </div>
    </section>
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
              <a href="#planos" className={cn(BTN_OUTLINE, 'h-11 px-5 text-base')}>
                Ver planos e preços
              </a>
            </div>
            <div className="mt-6 flex flex-wrap items-center gap-3">
              <p className="inline-flex items-center gap-1.5 rounded-md border border-border bg-card px-2.5 py-1 text-sm font-medium text-foreground">
                <WifiOff className="h-4 w-4 shrink-0 text-primary" aria-hidden="true" />
                Funciona sem internet
              </p>
              <a
                href="#instalar"
                className={cn('rounded-sm text-sm font-medium text-primary underline underline-offset-4', FOCUS_RING)}
              >
                Como instalar no computador e no celular
              </a>
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

        {/* Funciona sem internet */}
        <section
          id="offline"
          aria-labelledby="offline-title"
          className="scroll-mt-4 border-t border-border py-14 sm:py-20"
        >
          <div className={cn(SECTION, 'grid items-center gap-10 lg:grid-cols-[minmax(0,1.1fr)_minmax(0,1fr)] lg:gap-16')}>
            <div>
              <SectionHeading
                id="offline-title"
                title="A internet caiu? O escritório não para."
                description="Instale o FiscWise no computador e trabalhe sem medo de perder o que fez ou de ficar parado esperando a rede voltar."
              />
              <ul className="mt-8 space-y-5">
                {offlinePoints.map(({ icon: Icon, title, description }) => (
                  <li key={title} className="flex gap-3">
                    <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-accent text-primary">
                      <Icon className="h-5 w-5" aria-hidden="true" />
                    </span>
                    <div className="min-w-0">
                      <p className="text-base font-semibold text-foreground">{title}</p>
                      <p className="mt-1 text-sm text-muted-foreground">{description}</p>
                    </div>
                  </li>
                ))}
              </ul>
              <p className="mt-6 text-sm text-muted-foreground">
                O primeiro acesso em cada aparelho precisa de internet. Consulta à Receita, envio e download de
                documentos e geração do dossiê em PDF esperam a conexão voltar.
              </p>
            </div>
            <OfflineIllustration />
          </div>

          <div id="instalar" className={cn(SECTION, 'mt-12 scroll-mt-4')}>
            <div className="rounded-lg border border-primary/30 bg-accent/50 p-5 sm:p-6">
              <div className="flex flex-col gap-5 md:flex-row md:items-center md:justify-between">
                <div className="max-w-2xl">
                  <h3 className="text-lg font-semibold text-foreground">Instale o FiscWise em 1 clique</h3>
                  <p className="mt-1 text-sm text-muted-foreground">
                    Sem arquivo para baixar e sem configuração: o aplicativo é instalado pelo próprio navegador e
                    ganha atalho na área de trabalho ou na tela inicial.
                  </p>
                </div>
                <InstallAppButton
                  label="Instalar aplicativo"
                  compactLabel="Instalar aplicativo"
                  className={cn(BTN_PRIMARY, 'h-11 w-full shrink-0 px-5 text-base md:w-auto')}
                />
              </div>
              <ol className="mt-5 grid gap-4 border-t border-primary/15 pt-5 text-sm sm:grid-cols-3">
                {installSteps.map((step) => (
                  <li key={step.title} className="min-w-0">
                    <p className="font-semibold text-foreground">{step.title}</p>
                    <p className="mt-0.5 text-muted-foreground">{step.description}</p>
                  </li>
                ))}
              </ol>
            </div>
          </div>
        </section>

        {/* Como funciona */}
        <section
          id="como-funciona"
          aria-labelledby="como-funciona-title"
          className="scroll-mt-4 border-t border-border bg-card/60 py-14 sm:py-20"
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

        <PricingSection />

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
