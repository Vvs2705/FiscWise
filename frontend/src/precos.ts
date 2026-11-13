/*
 * Script da página estática /precos (precos.html). Sem React nem axios: só
 * aplica o tema e troca os cards pré-renderizados pelos preços atuais da API.
 */
import type { Plan } from '@/lib/hooks/useSubscription';
import { API_URL } from '@/lib/apiUrl';
import { renderPlanCards, renderPlansFallback } from '@/features/subscription/precosHtml';

function applyTheme() {
  let stored: string | null = null;
  try {
    stored = localStorage.getItem('fw-theme');
  } catch {
    // Armazenamento bloqueado: segue o sistema.
  }
  const dark = stored === 'dark' || (stored !== 'light' && matchMedia('(prefers-color-scheme: dark)').matches);
  document.documentElement.classList.toggle('dark', dark);
}

async function refreshPlans() {
  const target = document.getElementById('planos-lista');
  if (!target) return;
  const prerendered = target.querySelector('.plans') !== null;
  try {
    const res = await fetch(`${API_URL}/api/v1/subscription/plans`, { headers: { Accept: 'application/json' } });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const html = renderPlanCards((await res.json()) as Plan[]);
    if (html) target.innerHTML = html;
    else if (!prerendered) target.innerHTML = renderPlansFallback('error');
  } catch {
    // Sem rede ou API fora: mantém o que veio pré-renderizado do build.
    if (!prerendered) target.innerHTML = renderPlansFallback('error');
  }
}

applyTheme();
void refreshPlans();
