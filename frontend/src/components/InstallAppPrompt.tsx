import { Download, Share, Smartphone } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/Button';
import { isIosSafari, promptInstall, useInstallStore } from '@/lib/offline/install';

/**
 * Botão "Instalar aplicativo" (PWA). No iOS não existe prompt nativo:
 * mostra a instrução "Compartilhar → Adicionar à Tela de Início".
 */
export function InstallAppPrompt({ className }: { className?: string }) {
  const deferred = useInstallStore((s) => s.deferred);
  const installed = useInstallStore((s) => s.installed);

  if (installed) {
    return (
      <p className={className}>
        <span className="inline-flex items-center gap-2 text-sm text-muted-foreground">
          <Smartphone className="h-4 w-4" aria-hidden="true" />
          O FiscWise já está instalado neste dispositivo.
        </span>
      </p>
    );
  }

  if (isIosSafari()) {
    return (
      <div className={className}>
        <p className="flex items-start gap-2 text-sm text-muted-foreground">
          <Share className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
          <span>
            Para instalar no iPhone ou iPad, toque em <strong>Compartilhar</strong> e depois em{' '}
            <strong>Adicionar à Tela de Início</strong>.
          </span>
        </p>
      </div>
    );
  }

  return (
    <div className={className}>
      <Button
        variant="outline"
        size="sm"
        disabled={!deferred}
        onClick={async () => {
          const accepted = await promptInstall();
          if (accepted) toast.success('FiscWise instalado.');
        }}
        className="gap-2"
      >
        <Download className="h-4 w-4" aria-hidden="true" />
        Instalar aplicativo
      </Button>
      {!deferred && (
        <p className="mt-2 text-xs text-muted-foreground">
          Se o botão estiver indisponível, use o menu do navegador e escolha “Instalar aplicativo” ou “Adicionar à tela inicial”.
        </p>
      )}
    </div>
  );
}
