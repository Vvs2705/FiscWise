import { loadDriver } from '@/lib/tours';
import { getCurrentUser } from '@/lib/auth';

/**
 * Tour de boas-vindas: no primeiro acesso do contador, mostra passo a passo
 * as partes mais importantes do FiscWise (menu, ajuda e minicurso).
 * Fica marcado por usuário no navegador; dá para refazer pelo botão Ajuda.
 */

const KEY_PREFIX = 'fiscwise:tour-boas-vindas:';

function storageKey(): string {
  return `${KEY_PREFIX}${getCurrentUser()?.id ?? 'anon'}`;
}

export function hasSeenWelcomeTour(): boolean {
  try {
    return localStorage.getItem(storageKey()) === 'done';
  } catch {
    return true;
  }
}

function markWelcomeTourSeen() {
  try {
    localStorage.setItem(storageKey(), 'done');
  } catch {
    /* navegador sem storage: o tour pode voltar a aparecer, sem problema */
  }
}

const nav = (href: string) => `[data-tour="nav-${href}"]`;

let running = false;

export async function startWelcomeTour(): Promise<void> {
  if (running) return;
  running = true;
  const driver = await loadDriver();
  const firstName = getCurrentUser()?.full_name?.split(' ')[0];
  const d = driver({
    showProgress: true,
    smoothScroll: true,
    doneBtnText: 'Começar a usar',
    onDestroyed: () => {
      running = false;
      markWelcomeTourSeen();
    },
    steps: [
      {
        popover: {
          title: firstName ? `Boas-vindas, ${firstName}!` : 'Boas-vindas ao FiscWise!',
          description:
            'Em menos de um minuto você conhece as partes mais importantes da sua central do contador. Pode pular quando quiser e refazer depois pelo botão Ajuda.',
        },
      },
      {
        element: nav('/painel'),
        popover: {
          title: 'Painel',
          description: 'Seu resumo do dia: obrigações em aberto, clientes ativos, documentos para conferir e honorários em atraso.',
          side: 'right',
        },
      },
      {
        element: nav('/foco'),
        popover: {
          title: 'Foco de hoje',
          description: 'Tudo que pede ação hoje, em ordem de prioridade. O número vermelho mostra quantos itens são urgentes.',
          side: 'right',
        },
      },
      {
        element: nav('/clientes'),
        popover: {
          title: 'Clientes',
          description: 'Comece por aqui: cadastre seus clientes pelo CNPJ (os dados vêm da Receita) ou importe uma planilha.',
          side: 'right',
        },
      },
      {
        element: nav('/obrigacoes'),
        popover: {
          title: 'Obrigações',
          description: 'O FiscWise gera as obrigações de cada cliente conforme o regime. Você acompanha e dá baixa quando entregar.',
          side: 'right',
        },
      },
      {
        element: nav('/fechamento'),
        popover: {
          title: 'Fechamento mensal',
          description: 'Checklist do fechamento de cada cliente por competência, com score e dossiê em PDF no final.',
          side: 'right',
        },
      },
      {
        element: nav('/certificados'),
        popover: {
          title: 'Certificados',
          description: 'Cadastre os certificados digitais dos clientes. Você é avisado 30 dias antes de vencer.',
          side: 'right',
        },
      },
      {
        element: nav('/portal'),
        popover: {
          title: 'Portal do cliente',
          description: 'Seu cliente vê guias, documentos pedidos e o andamento do fechamento, sem ligar nem mandar e-mail.',
          side: 'right',
        },
      },
      {
        element: '[data-tour="ajuda"]',
        popover: {
          title: 'Ajuda em todas as páginas',
          description: 'Ficou com dúvida? Clique em Ajuda: aparece o passo a passo da tela em que você está.',
          side: 'bottom',
          align: 'end',
        },
      },
      {
        element: nav('/minicurso'),
        popover: {
          title: 'Minicurso FiscWise',
          description: 'Aulas em vídeo curtas mostrando cada tarefa sendo feita na tela, do começo ao fim.',
          side: 'right',
        },
      },
    ],
  });
  d.drive();
}

/** Inicia o tour sozinho no primeiro acesso (não durante testes automatizados). */
export function maybeStartWelcomeTour(): void {
  const forced = new URLSearchParams(window.location.search).get('tour') === '1';
  if (!forced && (hasSeenWelcomeTour() || navigator.webdriver)) return;
  void startWelcomeTour();
}
