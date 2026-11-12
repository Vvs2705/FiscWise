/**
 * Guia de cada página do app (botão "Ajuda" no topo).
 *
 * Cada entrada diz para que serve a tela e o passo a passo das tarefas mais
 * comuns. `lessonId` liga a página à aula do Minicurso FiscWise que mostra a
 * tarefa sendo feita; `tour` liga ao tour guiado da própria página.
 */

export type PageTourName = 'dashboard' | 'clients' | 'documents';

export interface GuideTask {
  title: string;
  steps: string[];
}

export interface PageGuide {
  /** Prefixo da rota (subrotas herdam: /clientes/:id usa /clientes). */
  path: string;
  title: string;
  summary: string;
  tasks: GuideTask[];
  tips?: string[];
  lessonId?: string;
  tour?: PageTourName;
}

export const PAGE_GUIDES: PageGuide[] = [
  {
    path: '/painel',
    title: 'Painel',
    summary:
      'Resumo do dia do escritório: o que vence, o que está atrasado e quais clientes precisam de atenção agora.',
    tasks: [
      {
        title: 'Começar o dia pelo que é urgente',
        steps: [
          'Olhe o quadro "Foco de hoje": ele junta obrigações em atraso, documentos para conferir e prazos do dia.',
          'Clique em "Resolver agora" para abrir a lista completa em ordem de prioridade.',
          'Use os números (obrigações em aberto, clientes ativos, documentos, recebíveis) para ir direto à tela de cada assunto.',
        ],
      },
      {
        title: 'Criar algo novo sem sair do painel',
        steps: [
          'Use os atalhos do topo: "Novo cliente", "Nova obrigação", "Enviar documento", "Cadastrar certificado" ou "Registrar guia".',
          'Preencha o formulário que abrir e clique em salvar. O painel atualiza sozinho.',
        ],
      },
    ],
    tips: ['Pressione Ctrl + K (ou Cmd + K no Mac) para buscar qualquer cliente ou tela.'],
    lessonId: 'primeiros-passos',
    tour: 'dashboard',
  },
  {
    path: '/foco',
    title: 'Foco de hoje',
    summary:
      'Lista única com tudo que pede ação, separada em crítico, hoje, esta semana, aguardando cliente e aguardando órgão.',
    tasks: [
      {
        title: 'Resolver as pendências do dia',
        steps: [
          'Comece pelo grupo "Crítico" e depois "Hoje".',
          'Em cada item, clique na ação principal (por exemplo "Resolver" ou "Renovar") para abrir a tela certa já no assunto.',
          'Itens "Aguardando cliente" mostram o que você já pediu e ainda não chegou: cobre pelo Portal do cliente ou WhatsApp.',
        ],
      },
    ],
    lessonId: 'primeiros-passos',
  },
  {
    path: '/clientes',
    title: 'Clientes',
    summary:
      'Carteira de clientes do escritório com regime tributário, contato, honorários e situação de cada empresa.',
    tasks: [
      {
        title: 'Cadastrar um cliente',
        steps: [
          'Clique em "Novo cliente", no canto superior direito.',
          'Digite o CNPJ: o FiscWise busca a razão social e o contato na Receita.',
          'Confira o nome, escolha o tipo (PJ ou PF) e o regime tributário.',
          'Preencha e-mail e telefone e clique em "Salvar cliente".',
        ],
      },
      {
        title: 'Importar vários clientes de uma vez',
        steps: [
          'Clique em "Modelo XLSX" para baixar a planilha modelo.',
          'Preencha uma linha por cliente e salve o arquivo.',
          'Clique em "Importar planilha" e escolha o arquivo.',
        ],
      },
      {
        title: 'Encontrar e gerenciar um cliente',
        steps: [
          'Digite nome, CNPJ/CPF ou e-mail na busca, ou filtre por tipo e regime.',
          'Clique em "Gerenciar" para abrir a central do cliente com obrigações, documentos, sócios e honorários.',
        ],
      },
    ],
    tips: ['Mantenha o regime tributário certo: é com ele que o FiscWise gera as obrigações do mês.'],
    lessonId: 'cadastrar-cliente',
    tour: 'clients',
  },
  {
    path: '/fechamento',
    title: 'Fechamento mensal',
    summary:
      'Esteira do fechamento de cada cliente por competência: checklist, notas, guias, obrigações e dossiê em PDF.',
    tasks: [
      {
        title: 'Criar o fechamento do mês',
        steps: [
          'Escolha a competência no seletor do topo.',
          'Clique em "Gerar rotina" para criar o fechamento de todos os clientes ativos.',
        ],
      },
      {
        title: 'Concluir o fechamento de um cliente',
        steps: [
          'Clique em "Abrir" na linha do cliente.',
          'Na aba "Checklist", marque cada etapa como concluída conforme avança.',
          'Quando o score chegar a 100%, clique em "Gerar dossiê" para baixar o PDF com o resumo do mês.',
        ],
      },
    ],
    tips: ['Clientes "Bloqueados" têm algo faltando (por exemplo, um extrato). O motivo aparece na coluna Bloqueios.'],
    lessonId: 'fechamento-mensal',
  },
  {
    path: '/obrigacoes',
    title: 'Obrigações',
    summary:
      'Calendário de obrigações fiscais dos clientes por competência, com prioridade, responsável e situação.',
    tasks: [
      {
        title: 'Gerar as obrigações do mês',
        steps: [
          'Escolha o mês no seletor do topo.',
          'Clique em "Gerar automáticas": o FiscWise cria as obrigações de cada cliente conforme o regime.',
        ],
      },
      {
        title: 'Acompanhar e dar baixa',
        steps: [
          'Filtre por cliente, status ou prioridade, ou busque pelo nome da obrigação.',
          'Clique em "Iniciar" quando começar a trabalhar na obrigação.',
          'Clique no ícone de confirmação (✓) para marcar como entregue.',
        ],
      },
      {
        title: 'Criar uma obrigação avulsa',
        steps: ['Clique em "Nova obrigação", escolha o cliente, o vencimento e a prioridade, e salve.'],
      },
    ],
    lessonId: 'obrigacoes',
  },
  {
    path: '/documentos',
    title: 'Documentos',
    summary: 'Esteira documental dos clientes: o que chegou, o que falta e o que está vencendo.',
    tasks: [
      {
        title: 'Enviar um documento',
        steps: [
          'Clique em enviar e escolha o cliente.',
          'Arraste o arquivo (PDF, XML, imagem ou planilha) ou clique para escolher.',
          'O FiscWise lê o arquivo e sugere o tipo e a competência. Confira e salve.',
        ],
      },
      {
        title: 'Ver ou cobrar um documento',
        steps: [
          'Clique no documento para abrir a pré-visualização ao lado.',
          'Documentos "Faltando" podem ser pedidos ao cliente pelo Portal do cliente.',
        ],
      },
    ],
    tour: 'documents',
  },
  {
    path: '/notas-fiscais',
    title: 'Notas fiscais',
    summary: 'Notas fiscais dos clientes: rascunhos, emitidas e canceladas.',
    tasks: [
      {
        title: 'Criar uma nota',
        steps: [
          'Clique em "Nova nota", escolha o cliente emissor e o tomador.',
          'Preencha serviço, valor e impostos e salve como rascunho.',
          'Abra a nota e clique em emitir quando estiver tudo certo.',
        ],
      },
    ],
  },
  {
    path: '/ecac',
    title: 'Central e-CAC',
    summary: 'Situação fiscal dos clientes na Receita Federal: pendências, mensagens e certidões.',
    tasks: [
      {
        title: 'Conferir pendências',
        steps: [
          'Escolha o cliente.',
          'Veja as pendências e mensagens encontradas e abra cada uma para os detalhes.',
        ],
      },
    ],
    tips: ['A consulta usa o certificado digital ou a procuração do cliente. Mantenha os dois em dia.'],
  },
  {
    path: '/guias',
    title: 'Guias e pagamentos',
    summary: 'Guias de impostos (DAS, DARF, FGTS e outras) com valor, vencimento e se já foram pagas.',
    tasks: [
      {
        title: 'Registrar e acompanhar uma guia',
        steps: [
          'Clique em registrar guia, escolha o cliente, o tipo, a competência, o valor e o vencimento.',
          'Envie a guia ao cliente pelo portal.',
          'Quando o cliente pagar, marque a guia como paga.',
        ],
      },
    ],
  },
  {
    path: '/caixa-postal-fiscal',
    title: 'Caixa postal fiscal',
    summary: 'Mensagens oficiais recebidas pelos clientes nos órgãos fiscais, em um só lugar.',
    tasks: [
      {
        title: 'Ler e tratar mensagens',
        steps: [
          'Filtre por cliente ou por mensagens não lidas.',
          'Abra a mensagem, leia o conteúdo e marque como tratada quando resolver.',
        ],
      },
    ],
  },
  {
    path: '/procuracoes',
    title: 'Procurações',
    summary: 'Procurações eletrônicas que os clientes deram ao escritório, com validade e alerta de vencimento.',
    tasks: [
      {
        title: 'Cadastrar uma procuração',
        steps: ['Clique em nova procuração, escolha o cliente, o órgão, os serviços e a validade, e salve.'],
      },
    ],
  },
  {
    path: '/certificados',
    title: 'Certificados',
    summary: 'Certificados digitais A1 e A3 dos clientes com aviso antes de vencer.',
    tasks: [
      {
        title: 'Cadastrar um certificado',
        steps: [
          'Clique em "Novo certificado".',
          'Escolha o cliente, dê um nome (por exemplo "e-CNPJ Padaria"), o tipo A1 ou A3 e a data de validade.',
          'Clique em salvar. O FiscWise avisa 30 dias antes de vencer.',
        ],
      },
      {
        title: 'Avisar o cliente da renovação',
        steps: ['No cartão do certificado que está vencendo, clique em "Avisar cliente".'],
      },
    ],
    lessonId: 'certificados',
  },
  {
    path: '/financeiro',
    title: 'Financeiro',
    summary: 'Honorários do escritório: cobranças, recebimentos e clientes inadimplentes.',
    tasks: [
      {
        title: 'Lançar e baixar honorários',
        steps: [
          'Crie a cobrança mensal de cada cliente (ou gere todas pelo valor de honorário do cadastro).',
          'Quando o cliente pagar, marque a cobrança como paga.',
          'Veja no relatório de inadimplência quem está em atraso.',
        ],
      },
    ],
  },
  {
    path: '/whatsapp',
    title: 'WhatsApp',
    summary: 'Conversas com os clientes pelo WhatsApp do escritório.',
    tasks: [
      {
        title: 'Responder um cliente',
        steps: ['Escolha a conversa na lista, digite a resposta e envie.'],
      },
    ],
  },
  {
    path: '/portal',
    title: 'Portal do cliente',
    summary:
      'Veja o portal como o seu cliente vê: fechamento, documentos pedidos, guias e pendências. Daqui você envia o acesso.',
    tasks: [
      {
        title: 'Dar acesso ao portal para um cliente',
        steps: [
          'Escolha o cliente no seletor do topo.',
          'Clique em "Enviar link de acesso ao portal" e confirme o e-mail.',
          'O cliente recebe um link e entra sem precisar criar senha.',
        ],
      },
      {
        title: 'Conferir o que o cliente vê',
        steps: ['Use as abas Visão geral, Documentos, Guias e Pendências.'],
      },
    ],
    lessonId: 'portal-cliente',
  },
  {
    path: '/relatorios',
    title: 'Relatórios',
    summary: 'Relatórios da carteira: produtividade, obrigações entregues, inadimplência e mais.',
    tasks: [
      {
        title: 'Gerar um relatório',
        steps: ['Escolha o relatório e o período, confira na tela e baixe em PDF ou planilha.'],
      },
    ],
  },
  {
    path: '/aprender',
    title: 'Aprender',
    summary: 'Checklist de ativação do escritório, guias rápidos, perguntas frequentes e tours guiados.',
    tasks: [
      {
        title: 'Deixar o escritório pronto',
        steps: ['Siga o "Checklist de ativação" e clique no botão de cada etapa que ainda falta.'],
      },
    ],
    lessonId: 'primeiros-passos',
  },
  {
    path: '/minicurso',
    title: 'Minicurso FiscWise',
    summary: 'Aulas em vídeo curtas mostrando cada tarefa sendo feita na tela, do começo ao fim.',
    tasks: [
      {
        title: 'Assistir às aulas',
        steps: [
          'Escolha uma aula na lista.',
          'Use os capítulos abaixo do vídeo para pular direto para um passo.',
          'A aula fica marcada como assistida quando você chega ao fim.',
        ],
      },
    ],
  },
  {
    path: '/configuracoes',
    title: 'Configurações',
    summary: 'Dados do escritório, sua conta, segurança (senha e verificação em duas etapas), equipe e plano.',
    tasks: [
      {
        title: 'Completar os dados do escritório',
        steps: ['Abra a aba do escritório, preencha CNPJ, CRC, endereço e contato, e salve.'],
      },
      {
        title: 'Ativar a verificação em duas etapas',
        steps: ['Abra a aba de segurança, clique para ativar e siga as instruções do aplicativo autenticador.'],
      },
    ],
  },
  {
    path: '/sincronizacao',
    title: 'Sincronização',
    summary: 'O FiscWise funciona sem internet. Aqui você vê o que ainda falta enviar e os aparelhos conectados.',
    tasks: [
      {
        title: 'Conferir se está tudo enviado',
        steps: [
          'Veja quantas alterações estão pendentes.',
          'Se aparecer erro, clique para tentar de novo quando a internet voltar.',
        ],
      },
    ],
  },
  {
    path: '/calculadora',
    title: 'Calculadora fiscal',
    summary: 'Simulações de impostos e do Fator R para comparar regimes.',
    tasks: [
      {
        title: 'Simular impostos',
        steps: ['Escolha o regime, preencha faturamento e folha e veja o resultado. Salve a simulação se quiser comparar depois.'],
      },
    ],
  },
];

export function getPageGuide(pathname: string): PageGuide | undefined {
  return PAGE_GUIDES.find((g) => pathname === g.path || pathname.startsWith(`${g.path}/`));
}
