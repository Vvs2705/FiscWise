/**
 * Prompt de instalação do PWA (OFFLINE_SYNC.md, seção 7.1).
 * `beforeinstallprompt` dispara uma vez, cedo, no carregamento: o listener é
 * registrado na importação deste módulo e o evento fica guardado no store.
 */
import { create } from 'zustand';

interface BeforeInstallPromptEvent extends Event {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: 'accepted' | 'dismissed' }>;
}

interface InstallState {
  deferred: BeforeInstallPromptEvent | null;
  installed: boolean;
  set: (patch: Partial<Omit<InstallState, 'set'>>) => void;
}

function detectStandalone(): boolean {
  if (typeof window === 'undefined') return false;
  const nav = navigator as Navigator & { standalone?: boolean };
  return (typeof window.matchMedia === 'function' && window.matchMedia('(display-mode: standalone)').matches) || nav.standalone === true;
}

export const useInstallStore = create<InstallState>((set) => ({
  deferred: null,
  installed: detectStandalone(),
  set: (patch) => set(patch),
}));

if (typeof window !== 'undefined') {
  window.addEventListener('beforeinstallprompt', (e) => {
    e.preventDefault();
    useInstallStore.getState().set({ deferred: e as BeforeInstallPromptEvent });
  });
  window.addEventListener('appinstalled', () => {
    useInstallStore.getState().set({ deferred: null, installed: true });
  });
}

export function isIosSafari(): boolean {
  if (typeof navigator === 'undefined') return false;
  const ua = navigator.userAgent;
  const ios = /iPhone|iPad|iPod/i.test(ua) || (ua.includes('Macintosh') && navigator.maxTouchPoints > 1);
  return ios && !/CriOS|FxiOS|EdgiOS/i.test(ua);
}

/** Abre o diálogo nativo de instalação. Devolve true se o usuário aceitou. */
export async function promptInstall(): Promise<boolean> {
  const { deferred, set } = useInstallStore.getState();
  if (!deferred) return false;
  await deferred.prompt();
  const choice = await deferred.userChoice;
  set({ deferred: null, installed: choice.outcome === 'accepted' });
  return choice.outcome === 'accepted';
}
