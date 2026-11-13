import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { toast } from 'sonner';
import { Clock, Download, Lock } from 'lucide-react';
import { useTenantInfo } from '@/lib/hooks/useSubscription';
import { dataOferta, useOferta } from '@/lib/hooks/useBilling';
import { useAuthStore } from '@/stores/authStore';
import { ACESSO_EXPIRADO_EVENT, getApiErrorMessage } from '@/lib/api';
import { downloadMyDataExport } from '@/lib/accountExport';
import { Button } from '@/components/ui/Button';
import { cn } from '@/lib/utils';

const LINK_ASSINAR =
  'inline-flex h-8 items-center rounded-md bg-primary px-3 text-sm font-medium text-primary-foreground ' +
  'hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring';

function diasRestantesTexto(dias: number): string {
  if (dias <= 0) return 'acaba hoje';
  return dias === 1 ? 'falta 1 dia' : `faltam ${dias} dias`;
}

/**
 * Faixa do teste grátis de 14 dias (abaixo do cabeçalho).
 * - Em teste: discreta, "Teste grátis: faltam N dias · Assinar" (destaque com 3 dias ou menos).
 * - Vencida (`acesso_expirado`): fixa, conta só para leitura, com Assinar e Exportar meus dados.
 * Um 402 ACESSO_EXPIRADO em qualquer tela recarrega a situação do escritório.
 */
export function TrialBanner() {
  const role = useAuthStore((s) => s.user?.role);
  const isOffice = !!role && role !== 'client';
  const isOwner = role === 'owner';
  const { data: tenant, refetch } = useTenantInfo(isOffice);
  const [exporting, setExporting] = useState(false);
  // Oferta de reconquista: só o dono, só com a conta vencida.
  const { data: oferta } = useOferta(isOwner && !!tenant?.acesso_expirado);

  useEffect(() => {
    if (!isOffice) return;
    const onExpirado = () => void refetch();
    window.addEventListener(ACESSO_EXPIRADO_EVENT, onExpirado);
    return () => window.removeEventListener(ACESSO_EXPIRADO_EVENT, onExpirado);
  }, [isOffice, refetch]);

  if (!isOffice || !tenant) return null;

  async function handleExport() {
    setExporting(true);
    try {
      await downloadMyDataExport();
      toast.success('Exportação concluída.');
    } catch (err) {
      toast.error(getApiErrorMessage(err, 'Não foi possível exportar seus dados.'));
    } finally {
      setExporting(false);
    }
  }

  if (tenant.acesso_expirado) {
    return (
      <div
        role="alert"
        className="flex flex-wrap items-center gap-x-3 gap-y-2 border-b border-destructive/30 bg-destructive/10 px-4 py-2 text-sm text-foreground md:px-6"
      >
        <Lock className="h-4 w-4 shrink-0 text-destructive" aria-hidden="true" />
        <p className="min-w-0 flex-1">
          <strong className="font-semibold">Seu teste acabou.</strong> A conta está só para leitura.{' '}
          {isOwner ? 'Assine para voltar a editar.' : 'Peça ao responsável pelo escritório para assinar um plano.'}
          {isOwner && oferta?.ativa && (
            <>
              {' '}
              <strong className="font-semibold text-success">
                Oferta especial até {dataOferta(oferta.expires_at)}: 15% no 1º mês ou anual com 25%.
              </strong>
            </>
          )}
        </p>
        <div className="flex flex-wrap items-center gap-2">
          {isOwner && (
            <Link to={oferta?.ativa ? '/assinatura?oferta=1' : '/assinatura'} className={LINK_ASSINAR}>
              {oferta?.ativa ? 'Ver oferta' : 'Assinar'}
            </Link>
          )}
          <Button variant="outline" size="sm" onClick={handleExport} loading={exporting}>
            <Download className="h-4 w-4" aria-hidden="true" />
            Exportar meus dados
          </Button>
        </div>
      </div>
    );
  }

  if (!tenant.em_teste || tenant.trial_dias_restantes == null) return null;

  const dias = tenant.trial_dias_restantes;
  const urgente = dias <= 3;

  return (
    <div
      role="status"
      className={cn(
        'flex flex-wrap items-center gap-x-3 gap-y-1 border-b px-4 py-1.5 text-sm md:px-6',
        urgente ? 'border-warning/30 bg-warning/10 text-foreground' : 'border-border bg-muted/40 text-muted-foreground',
      )}
    >
      <Clock className={cn('h-4 w-4 shrink-0', urgente ? 'text-warning' : 'text-muted-foreground')} aria-hidden="true" />
      <p className="min-w-0 flex-1">
        <span className={cn(urgente && 'font-semibold text-foreground')}>Teste grátis: {diasRestantesTexto(dias)}</span>
        {urgente && ' — depois, sem assinatura, a conta fica só para leitura.'}
      </p>
      {isOwner && (
        <Link
          to="/assinatura"
          className={urgente ? LINK_ASSINAR : 'text-sm font-medium text-primary hover:underline'}
        >
          Assinar
        </Link>
      )}
    </div>
  );
}
