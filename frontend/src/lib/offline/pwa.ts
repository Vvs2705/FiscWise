/**
 * Registro do service worker (vite-plugin-pwa, registerType 'prompt').
 * Com sessão aberta, a versão nova só assume quando o usuário clica em
 * "Atualizar": recarregar sozinho no meio de um formulário perderia o que
 * ainda não foi salvo. Sem sessão, atualiza na hora.
 */
import { registerSW } from 'virtual:pwa-register';
import { toast } from 'sonner';
import { isAuthenticated } from '@/lib/auth';

let registered = false;

export function registerServiceWorker(): void {
  if (registered || typeof window === 'undefined' || !('serviceWorker' in navigator)) return;
  registered = true;
  const updateSW = registerSW({
    immediate: true,
    onNeedRefresh() {
      // Visitante sem sessão (página inicial, login) não tem nada a perder:
      // assume a versão nova na hora, para nunca ver uma página antiga do site.
      if (!isAuthenticated()) {
        void updateSW(true);
        return;
      }
      toast('Nova versão do FiscWise disponível', {
        description: 'Atualize para usar a versão mais recente. Suas alterações locais ficam guardadas.',
        duration: Infinity,
        action: { label: 'Atualizar', onClick: () => void updateSW(true) },
      });
    },
    onOfflineReady() {
      // Nas páginas públicas (visitante sem sessão) o aviso não cabe: a página
      // inicial e o login só anunciam o que o visitante pode usar ali.
      if (!isAuthenticated()) return;
      toast.success('FiscWise pronto para uso sem internet.');
    },
  });
}
