import { Download } from 'lucide-react';
import { toast } from 'sonner';
import { isIosSafari, promptInstall, useInstallStore } from '@/lib/offline/install';
import { cn } from '@/lib/utils';

/** Passo a passo quando o navegador não oferece o diálogo de instalação. */
function installInstructions(): string {
  if (isIosSafari()) {
    return 'No iPhone ou iPad, toque em Compartilhar e depois em “Adicionar à Tela de Início”.';
  }
  if (typeof navigator !== 'undefined' && /Android/i.test(navigator.userAgent)) {
    return 'No Android, abra o menu ⋮ do navegador e escolha “Instalar app” ou “Adicionar à tela inicial”.';
  }
  return 'No Chrome ou no Edge, clique no ícone de instalar no fim da barra de endereço, ou abra o menu ⋮ do navegador e escolha “Instalar”.';
}

/**
 * Botão "Instalar aplicativo" (PWA) sempre visível enquanto o FiscWise não
 * estiver instalado neste aparelho. Com o diálogo nativo disponível, abre o
 * diálogo; sem ele (iOS, Firefox, prompt já recusado), mostra o passo a passo.
 */
export function InstallAppButton({
  className,
  label = 'Instalar aplicativo',
  compactLabel,
}: {
  className?: string;
  label?: string;
  /** Texto curto em telas pequenas; sem ele, só o ícone aparece em < sm. */
  compactLabel?: string;
}) {
  const installed = useInstallStore((s) => s.installed);
  if (installed) return null;

  return (
    <button
      type="button"
      onClick={async () => {
        if (useInstallStore.getState().deferred) {
          const accepted = await promptInstall();
          if (accepted) toast.success('FiscWise instalado. Ele abre pelo atalho na área de trabalho ou na tela inicial.');
          return;
        }
        toast.info('Como instalar o FiscWise', { description: installInstructions(), duration: 12000 });
      }}
      className={cn(
        'inline-flex select-none items-center justify-center gap-2 whitespace-nowrap rounded-md font-medium',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background',
        className,
      )}
    >
      <Download className="h-4 w-4 shrink-0" aria-hidden="true" />
      {compactLabel ? (
        <>
          <span className="sm:hidden">{compactLabel}</span>
          <span className="hidden sm:inline">{label}</span>
        </>
      ) : (
        <span className="sr-only sm:not-sr-only">{label}</span>
      )}
    </button>
  );
}
