import { driver } from 'driver.js';
import 'driver.js/dist/driver.css';
import { NavigateFunction } from 'react-router-dom';

export function runDashboardTour() {
  const d = driver({
    showProgress: true,
    steps: [
      {
        element: '#tour-welcome',
        popover: {
          title: 'Bem-vindo ao FiscWise! 👋',
          description: 'Esta é a sua central de controle diário. Vamos fazer um tour rápido pelas principais funcionalidades.',
          side: 'bottom',
          align: 'start',
        },
      },
      {
        element: '#tour-focus',
        popover: {
          title: '🎯 Foco de Hoje',
          description: 'Aqui você vê as pendências fiscais críticas de hoje (obrigações vencendo, guias em atraso, etc.). Comece seu dia por este painel.',
          side: 'bottom',
          align: 'start',
        },
      },
      {
        element: '#tour-risk',
        popover: {
          title: '📈 Saúde da Carteira',
          description: 'Um indicador de 0 a 100 mostrando a saúde fiscal geral dos seus clientes.',
          side: 'left',
          align: 'start',
        },
      },
      {
        element: '#tour-deadlines',
        popover: {
          title: '📅 Agenda Semanal',
          description: 'Acompanhe de forma clara os vencimentos de impostos e obrigações para a semana corrente.',
          side: 'top',
          align: 'start',
        },
      },
      {
        element: '#tour-attention',
        popover: {
          title: '⚠️ Clientes que precisam de atenção',
          description: 'Uma lista priorizada indicando exatamente quais clientes exigem alguma ação imediata.',
          side: 'top',
          align: 'start',
        },
      },
    ],
  });
  d.drive();
}

export function runClientsTour() {
  const d = driver({
    showProgress: true,
    steps: [
      {
        element: '#tour-clients-title',
        popover: {
          title: '💼 Carteira de Clientes',
          description: 'Gerencie todos os dados de contato, regimes tributários e status operacionais dos seus clientes.',
          side: 'bottom',
          align: 'start',
        },
      },
      {
        element: '#tour-clients-search',
        popover: {
          title: '🔍 Busca e Filtros Rápidos',
          description: 'Procure por clientes por nome ou CNPJ/CPF, filtre por regime tributário (Simples Nacional, MEI, etc.) de forma instantânea.',
          side: 'bottom',
          align: 'start',
        },
      },
      {
        element: '#tour-clients-table',
        popover: {
          title: '📋 Listagem Inteligente',
          description: 'Acompanhe a saúde operacional de cada cliente e clique em "Gerenciar" para abrir a Central do Cliente.',
          side: 'top',
          align: 'start',
        },
      },
    ],
  });
  d.drive();
}

export function runDocumentsTour() {
  const d = driver({
    showProgress: true,
    steps: [
      {
        element: '#tour-docs-upload',
        popover: {
          title: '📤 Upload de Documentos',
          description: 'Envie ou solicite arquivos. A inteligência artificial do FiscWise lerá e categorizará o conteúdo automaticamente.',
          side: 'bottom',
          align: 'start',
        },
      },
      {
        element: '#tour-docs-table',
        popover: {
          title: '📂 Repositório de Documentos',
          description: 'Aqui fica toda a esteira documental. Veja detalhes e pré-visualizações inline de PDFs e imagens sem sair do app.',
          side: 'top',
          align: 'start',
        },
      },
    ],
  });
  d.drive();
}

export function startTour(tourName: 'dashboard' | 'clients' | 'documents', navigate: NavigateFunction, currentPath: string) {
  if (tourName === 'dashboard') {
    if (currentPath !== '/dashboard') {
      navigate('/dashboard');
      setTimeout(() => {
        runDashboardTour();
      }, 500);
    } else {
      runDashboardTour();
    }
  } else if (tourName === 'clients') {
    if (currentPath !== '/clientes') {
      navigate('/clientes');
      setTimeout(() => {
        runClientsTour();
      }, 500);
    } else {
      runClientsTour();
    }
  } else if (tourName === 'documents') {
    if (currentPath !== '/documentos') {
      navigate('/documentos');
      setTimeout(() => {
        runDocumentsTour();
      }, 500);
    } else {
      runDocumentsTour();
    }
  }
}
