'use client';
import { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  BookOpen,
  CheckCircle2,
  Circle,
  Play,
  ArrowRight,
  HelpCircle,
  Sparkles,
  ChevronDown,
  Building,
  CreditCard,
  FolderOpen,
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import {
  useClients,
  useCertificates,
  useReceivables,
  useDocuments,
} from '@/lib/hooks/useOperations';
import { startTour } from '@/lib/tours';

export function LearningPage() {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<'checklist' | 'tutorials' | 'tours'>('checklist');
  const [expandedFAQ, setExpandedFAQ] = useState<number | null>(null);

  // Load real operational states for activation progress
  const { data: clients } = useClients();
  const { data: certificates } = useCertificates();
  const { data: receivables } = useReceivables();
  const { data: documents } = useDocuments();

  const isProfileComplete = true; // Simulating email verify/profile setup as complete
  const hasClients = (clients?.length ?? 0) > 0;
  const hasCertificates = (certificates?.length ?? 0) > 0;
  const hasReceivables = (receivables?.length ?? 0) > 0;
  const hasDocuments = (documents?.length ?? 0) > 0;

  // Checklist items configuration
  const checklistItems = useMemo(() => [
    {
      id: 'profile',
      title: 'Configurar Perfil',
      description: 'Defina suas preferências de segurança e dados contábeis.',
      completed: isProfileComplete,
      actionLabel: 'Ir para configurações',
      action: () => navigate('/configuracoes'),
    },
    {
      id: 'clients',
      title: 'Cadastrar seu Primeiro Cliente',
      description: 'Adicione uma empresa na sua carteira operacional.',
      completed: hasClients,
      actionLabel: 'Adicionar cliente',
      action: () => navigate('/clientes', { state: { openCreate: true } }),
    },
    {
      id: 'certificates',
      title: 'Vincular Certificado Digital',
      description: 'Cadastre um certificado A1/A3 para acompanhar validades.',
      completed: hasCertificates,
      actionLabel: 'Cadastrar certificado',
      action: () => navigate('/certificados'),
    },
    {
      id: 'billing',
      title: 'Configurar Primeiro Honorário',
      description: 'Crie uma cobrança mensal para automatizar recebimentos.',
      completed: hasReceivables,
      actionLabel: 'Definir cobrança',
      action: () => navigate('/financeiro', { state: { openCreate: true } }),
    },
    {
      id: 'documents',
      title: 'Processar Primeiro Documento',
      description: 'Faça upload de uma guia ou balanço para testes de IA.',
      completed: hasDocuments,
      actionLabel: 'Enviar arquivo',
      action: () => navigate('/documentos'),
    },
  ], [isProfileComplete, hasClients, hasCertificates, hasReceivables, hasDocuments, navigate]);

  const completedCount = checklistItems.filter((i) => i.completed).length;
  const progressPercent = Math.round((completedCount / checklistItems.length) * 100);

  const faqs = [
    {
      question: 'Como funciona o motor de obrigações?',
      answer: 'O FiscWise escaneia no dia 1 de cada mês as regras fiscais ativas dos seus clientes e gera automaticamente os cards de checklist na sua Agenda e Obrigações. Isso evita que você precise cadastrar tarefas recorrentes manualmente.',
    },
    {
      question: 'Como a Inteligência Artificial processa os uploads?',
      answer: 'Ao arrastar arquivos na esteira de documentos, a nossa IA realiza OCR no PDF/imagem, detecta qual o tipo de guia contábil (DAS, DASN, Balancetes), valida a competência, lê os valores principais e extrai os metadados de forma estruturada.',
    },
    {
      question: 'Posso notificar meus clientes sobre impostos a vencer?',
      answer: 'Sim! Na tela de Certificados ou Documentos, ao identificar um vencimento próximo ou guia disponível, clique em "Notificar" ou "Avisar Cliente". O sistema preparará um resumo por e-mail ou WhatsApp com o link do portal do cliente.',
    },
    {
      question: 'O que é o "Score de Saúde da Carteira"?',
      answer: 'É uma métrica proprietária de 0 a 100 calculada com base nas obrigações atrasadas, documentos em aberto e recebíveis vencidos da sua carteira. Manter o score acima de 90 indica que sua rotina contábil está em dia e segura.',
    },
  ];

  return (
    <div className="space-y-6">
      {/* Header section with premium design */}
      <div className="relative overflow-hidden rounded-[24px] border border-border/50 bg-card/45 p-6 md:p-8 backdrop-blur-sm shadow-md">
        <div className="relative z-10 max-w-3xl space-y-3">
          <div className="flex items-center gap-2 text-xs font-semibold text-teal-500 uppercase tracking-widest dark:text-teal-400">
            <Sparkles className="h-4 w-4" />
            <span>Academia Contábil</span>
          </div>
          <h1 className="bg-gradient-to-r from-teal-500 via-emerald-500 to-sky-500 bg-clip-text text-3xl font-extrabold tracking-tight text-transparent dark:from-teal-400 dark:via-emerald-400 dark:to-sky-400">
            Central de Aprendizado FiscWise
          </h1>
          <p className="text-sm md:text-base text-muted-foreground leading-relaxed">
            Domine as ferramentas do FiscWise, acompanhe o progresso de configuração do seu ambiente e aprenda a otimizar sua rotina contábil.
          </p>
        </div>
        {/* Background glow decoration */}
        <div className="absolute right-0 top-0 -z-0 h-64 w-64 rounded-full bg-teal-500/10 blur-3xl" />
        <div className="absolute left-1/3 bottom-0 -z-0 h-48 w-48 rounded-full bg-sky-500/10 blur-3xl" />
      </div>

      {/* Tabs selector */}
      <div className="flex border-b border-border/40 gap-4">
        <button
          onClick={() => setActiveTab('checklist')}
          className={`pb-3 text-sm font-semibold transition-all relative ${
            activeTab === 'checklist'
              ? 'text-teal-400 border-b-2 border-teal-400'
              : 'text-muted-foreground hover:text-foreground'
          }`}
        >
          Checklist de Ativação
        </button>
        <button
          onClick={() => setActiveTab('tutorials')}
          className={`pb-3 text-sm font-semibold transition-all relative ${
            activeTab === 'tutorials'
              ? 'text-teal-400 border-b-2 border-teal-400'
              : 'text-muted-foreground hover:text-foreground'
          }`}
        >
          Guias e FAQs
        </button>
        <button
          onClick={() => setActiveTab('tours')}
          className={`pb-3 text-sm font-semibold transition-all relative ${
            activeTab === 'tours'
              ? 'text-teal-400 border-b-2 border-teal-400'
              : 'text-muted-foreground hover:text-foreground'
          }`}
        >
          Tours Guiados
        </button>
      </div>

      {/* Checklist View */}
      {activeTab === 'checklist' && (
        <div className="grid gap-6 lg:grid-cols-[1fr_2fr]">
          {/* Progress Widget */}
          <Card className="bg-card/45 backdrop-blur-sm border-border/50 h-fit">
            <CardHeader>
              <CardTitle className="text-lg font-bold">Seu Progresso</CardTitle>
              <CardDescription>
                Complete as etapas para ativar 100% o seu ambiente de trabalho contábil.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="flex flex-col items-center justify-center py-4">
                <div className="relative flex items-center justify-center">
                  {/* Progress ring or score label */}
                  <div className="text-4xl font-extrabold text-teal-400">{progressPercent}%</div>
                </div>
                <div className="text-xs text-muted-foreground font-semibold mt-3 text-center">
                  {completedCount} de {checklistItems.length} tarefas completadas
                </div>
              </div>

              {/* Progress bar */}
              <div className="h-2 bg-muted rounded-full overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-teal-400 to-emerald-500 rounded-full transition-all duration-500"
                  style={{ width: `${progressPercent}%` }}
                />
              </div>

              <div className="bg-muted/20 border rounded-xl p-4 text-xs leading-relaxed text-muted-foreground">
                <span className="font-semibold text-foreground block mb-1">🎉 Quase pronto!</span>
                Após cadastrar o primeiro cliente e configurar honorários, a esteira de alertas estará ativa no seu celular e e-mail.
              </div>
            </CardContent>
          </Card>

          {/* Checklist Items list */}
          <div className="space-y-4">
            {checklistItems.map((item) => (
              <Card
                key={item.id}
                className={`transition-all border-border/50 bg-card/40 ${
                  item.completed
                    ? 'border-emerald-500/25 bg-emerald-500/5'
                    : 'hover:border-primary/30'
                }`}
              >
                <CardContent className="p-5 flex items-start gap-4">
                  {item.completed ? (
                    <CheckCircle2 className="h-6 w-6 text-emerald-400 shrink-0 mt-0.5" />
                  ) : (
                    <Circle className="h-6 w-6 text-muted-foreground/50 shrink-0 mt-0.5" />
                  )}
                  <div className="flex-1 space-y-1">
                    <div className="flex items-center justify-between gap-4">
                      <h4 className={`font-bold text-base ${item.completed ? 'text-emerald-400/90 line-through' : 'text-foreground'}`}>
                        {item.title}
                      </h4>
                      {!item.completed && (
                        <Button
                          size="sm"
                          onClick={item.action}
                          className="h-8 text-xs bg-primary/10 text-primary border border-primary/20 hover:bg-primary/20 shrink-0"
                        >
                          {item.actionLabel}
                          <ArrowRight className="h-3.5 w-3.5 ml-1" />
                        </Button>
                      )}
                    </div>
                    <p className="text-sm text-muted-foreground leading-relaxed">{item.description}</p>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      )}

      {/* Tutorials & FAQs View */}
      {activeTab === 'tutorials' && (
        <div className="grid gap-6 md:grid-cols-2">
          {/* Quick Tutorials Grid */}
          <div className="space-y-6">
            <h3 className="flex items-center gap-2 text-xl font-bold text-foreground">
              <BookOpen className="h-5 w-5 text-teal-400" />
              Guias Rápidos de Gestão
            </h3>

            <div className="grid gap-4">
              <Card className="bg-card/45 backdrop-blur-sm border-border/50 hover:border-primary/35 transition-all">
                <CardHeader className="pb-2">
                  <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-teal-500/10 border border-teal-500/20 text-teal-400 mb-2">
                    <Building className="h-4 w-4" />
                  </div>
                  <CardTitle className="text-base font-bold">Gestão de Carteira</CardTitle>
                </CardHeader>
                <CardContent className="text-sm text-muted-foreground leading-relaxed">
                  Aprenda a estruturar seu cadastro de clientes contábeis. Mantenha os regimes tributários atualizados (MEI, Simples Nacional, Lucro Presumido) para permitir que o motor de obrigações calcule os prazos fiscais de forma correta.
                </CardContent>
              </Card>

              <Card className="bg-card/45 backdrop-blur-sm border-border/50 hover:border-primary/35 transition-all">
                <CardHeader className="pb-2">
                  <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-teal-500/10 border border-teal-500/20 text-teal-400 mb-2">
                    <FolderOpen className="h-4 w-4" />
                  </div>
                  <CardTitle className="text-base font-bold">Esteira Inteligente de Arquivos</CardTitle>
                </CardHeader>
                <CardContent className="text-sm text-muted-foreground leading-relaxed">
                  Arraste arquivos PDF, XML ou XLS diretamente na tela de documentos. O FiscWise classificará o documento via IA, lerá o imposto, a competência e registrará o valor, alimentando o painel de compliance automaticamente.
                </CardContent>
              </Card>

              <Card className="bg-card/45 backdrop-blur-sm border-border/50 hover:border-primary/35 transition-all">
                <CardHeader className="pb-2">
                  <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-teal-500/10 border border-teal-500/20 text-teal-400 mb-2">
                    <CreditCard className="h-4 w-4" />
                  </div>
                  <CardTitle className="text-base font-bold">Honorários Recorrentes</CardTitle>
                </CardHeader>
                <CardContent className="text-sm text-muted-foreground leading-relaxed">
                  Defina o valor do honorário contábil e o dia de vencimento na Central do Cliente. O FiscWise gerará automaticamente os recebíveis todos os meses, alimentando o fluxo financeiro e o relatório de inadimplência.
                </CardContent>
              </Card>
            </div>
          </div>

          {/* FAQs Accordion */}
          <div className="space-y-6">
            <h3 className="flex items-center gap-2 text-xl font-bold text-foreground">
              <HelpCircle className="h-5 w-5 text-teal-400" />
              Perguntas Frequentes (FAQ)
            </h3>

            <div className="space-y-3">
              {faqs.map((faq, index) => {
                const isExpanded = expandedFAQ === index;
                return (
                  <Card
                    key={index}
                    className="bg-card/45 backdrop-blur-sm border-border/50 overflow-hidden"
                  >
                    <button
                      onClick={() => setExpandedFAQ(isExpanded ? null : index)}
                      className="flex w-full items-center justify-between p-4 text-left font-bold text-sm text-foreground hover:text-teal-400 transition-colors"
                    >
                      <span>{faq.question}</span>
                      <ChevronDown
                        className={`h-4 w-4 shrink-0 text-muted-foreground transition-transform duration-200 ${
                          isExpanded ? 'rotate-180 text-teal-400' : ''
                        }`}
                      />
                    </button>
                    {isExpanded && (
                      <div className="px-4 pb-4 text-sm text-muted-foreground leading-relaxed border-t border-border/30 pt-3">
                        {faq.answer}
                      </div>
                    )}
                  </Card>
                );
              })}
            </div>
          </div>
        </div>
      )}

      {/* Guided Tours View */}
      {activeTab === 'tours' && (
        <div className="space-y-6">
          <div>
            <h3 className="flex items-center gap-2 text-xl font-bold text-foreground">
              <Play className="h-5 w-5 text-teal-400" />
              Tours Guiados e Interativos
            </h3>
            <p className="text-sm text-muted-foreground mt-1">
              Inicie um passo a passo visual nas principais telas do sistema para entender onde fica cada recurso.
            </p>
          </div>

          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            <Card className="bg-card/45 backdrop-blur-sm border-border/50 hover:border-primary/35 transition-all p-5 flex flex-col justify-between h-48">
              <div>
                <span className="text-[10px] uppercase font-bold text-primary tracking-wider">Passo a passo 1</span>
                <h4 className="mt-1 text-lg font-bold leading-snug text-foreground">Tour do Painel Cockpit</h4>
                <p className="text-xs text-muted-foreground mt-2 leading-relaxed">
                  Entenda o Foco de Hoje, o indicador de Saúde da Carteira e a lista de prioridades diárias.
                </p>
              </div>
              <Button
                onClick={() => startTour('dashboard', navigate, '/aprender')}
                size="sm"
                className="w-fit bg-primary/10 text-primary border border-primary/20 hover:bg-primary/20 gap-1.5"
              >
                <Play className="h-3.5 w-3.5 fill-primary" />
                Iniciar Tour
              </Button>
            </Card>

            <Card className="bg-card/45 backdrop-blur-sm border-border/50 hover:border-primary/35 transition-all p-5 flex flex-col justify-between h-48">
              <div>
                <span className="text-[10px] uppercase font-bold text-primary tracking-wider">Passo a passo 2</span>
                <h4 className="mt-1 text-lg font-bold leading-snug text-foreground">Tour de Carteira de Clientes</h4>
                <p className="text-xs text-muted-foreground mt-2 leading-relaxed">
                  Aprenda a buscar, filtrar regimes tributários e abrir a cockpit de detalhe de um cliente.
                </p>
              </div>
              <Button
                onClick={() => startTour('clients', navigate, '/aprender')}
                size="sm"
                className="w-fit bg-primary/10 text-primary border border-primary/20 hover:bg-primary/20 gap-1.5"
              >
                <Play className="h-3.5 w-3.5 fill-primary" />
                Iniciar Tour
              </Button>
            </Card>

            <Card className="bg-card/45 backdrop-blur-sm border-border/50 hover:border-primary/35 transition-all p-5 flex flex-col justify-between h-48">
              <div>
                <span className="text-[10px] uppercase font-bold text-primary tracking-wider">Passo a passo 3</span>
                <h4 className="mt-1 text-lg font-bold leading-snug text-foreground">Tour de Esteira Documental</h4>
                <p className="text-xs text-muted-foreground mt-2 leading-relaxed">
                  Entenda onde enviar arquivos, onde ver a classificação da IA e o preview lateral.
                </p>
              </div>
              <Button
                onClick={() => startTour('documents', navigate, '/aprender')}
                size="sm"
                className="w-fit bg-primary/10 text-primary border border-primary/20 hover:bg-primary/20 gap-1.5"
              >
                <Play className="h-3.5 w-3.5 fill-primary" />
                Iniciar Tour
              </Button>
            </Card>
          </div>
        </div>
      )}
    </div>
  );
}
