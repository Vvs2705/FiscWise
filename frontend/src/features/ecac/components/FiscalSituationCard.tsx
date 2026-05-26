import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { useFiscalSituation, useRefreshFiscalSituation } from '../hooks/useEcac';
import { RefreshCw, CheckCircle2, AlertCircle } from 'lucide-react';
import toast from 'react-hot-toast';

interface FiscalSituationCardProps {
  clientId: string;
}

export function FiscalSituationCard({ clientId }: FiscalSituationCardProps) {
  const { data: situation, isLoading, refetch } = useFiscalSituation(clientId);
  const refresh = useRefreshFiscalSituation();

  const handleRefresh = async () => {
    try {
      await refresh.mutateAsync(clientId);
      toast.success('Consulta fiscal solicitada no e-CAC!');
      refetch();
    } catch (err) {
      toast.error('Erro ao consultar e-CAC.');
    }
  };

  if (isLoading) {
    return (
      <Card className="border-border/60 bg-card">
        <CardContent className="flex items-center justify-center p-8">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent" />
        </CardContent>
      </Card>
    );
  }

  if (!situation) {
    return (
      <Card className="border-border/60 bg-card">
        <CardContent className="flex flex-col items-center justify-center p-8 text-center space-y-3">
          <AlertCircle className="h-8 w-8 text-muted-foreground" />
          <div>
            <h3 className="font-semibold text-sm">Sem dados de situação fiscal</h3>
            <p className="text-xs text-muted-foreground mt-1">
              Este cliente ainda não possui uma consulta e-CAC arquivada.
            </p>
          </div>
          <Button
            size="sm"
            onClick={handleRefresh}
            disabled={refresh.isPending}
            className="flex items-center gap-2"
          >
            <RefreshCw className="h-4 w-4" />
            Consultar Situação Fiscal
          </Button>
        </CardContent>
      </Card>
    );
  }

  const isRegular = situation.status_geral?.toLowerCase() === 'regular';

  return (
    <Card className="border-border/60 bg-card">
      <CardHeader className="flex flex-row items-center justify-between pb-3">
        <CardTitle className="text-sm font-semibold tracking-wider uppercase text-muted-foreground">
          Situação Fiscal Federal (e-CAC)
        </CardTitle>
        <Button
          variant="outline"
          size="sm"
          onClick={handleRefresh}
          disabled={refresh.isPending}
          className="flex items-center gap-2 h-8"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${refresh.isPending ? 'animate-spin' : ''}`} />
          Atualizar
        </Button>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-center justify-between p-4 rounded-lg bg-muted/10 border border-border/30">
          <div className="flex items-center gap-3">
            {isRegular ? (
              <CheckCircle2 className="h-6 w-6 text-emerald-500" />
            ) : (
              <AlertCircle className="h-6 w-6 text-red-500" />
            )}
            <div>
              <p className="text-xs text-muted-foreground">Status Geral CNPJ</p>
              <p className="text-sm font-semibold text-foreground mt-0.5">
                {situation.status_geral?.toUpperCase() || 'NÃO CONSULTADO'}
              </p>
            </div>
          </div>
          <Badge variant={isRegular ? 'success' : 'error'}>
            {isRegular ? 'Regularizado' : 'Pendências Encontradas'}
          </Badge>
        </div>

        <div className="grid gap-4 sm:grid-cols-2 text-sm">
          <div>
            <p className="text-xs text-muted-foreground">Status da Certidão Conjunta (CND)</p>
            <div className="flex items-center gap-2 mt-1">
              <Badge variant={situation.certidao_status === 'ativa' || situation.certidao_status === 'valida' ? 'success' : 'error'}>
                {situation.certidao_status?.toUpperCase() || 'INEXISTENTE'}
              </Badge>
              {situation.certidao_validade && (
                <span className="text-xs text-muted-foreground">
                  Válida até: {new Date(situation.certidao_validade + 'T00:00:00').toLocaleDateString('pt-BR')}
                </span>
              )}
            </div>
          </div>

          <div>
            <p className="text-xs text-muted-foreground">Última consulta e-CAC</p>
            <p className="text-sm font-medium text-foreground mt-1">
              {new Date(situation.consultado_em).toLocaleString('pt-BR')}
            </p>
          </div>
        </div>

        {/* Debts / Pendencies list */}
        {!isRegular && (
          <div className="space-y-3 border-t border-border/40 pt-3">
            {situation.pendencias && (
              <div>
                <span className="text-xs font-semibold text-red-500 block uppercase tracking-wider">
                  Declarações Pendentes / Atrasadas
                </span>
                <ul className="list-disc pl-4 text-xs space-y-1 mt-1 text-muted-foreground">
                  {Array.isArray(situation.pendencias) ? (
                    situation.pendencias.map((p, idx) => <li key={idx}>{p}</li>)
                  ) : (
                    <li>{String(situation.pendencias)}</li>
                  )}
                </ul>
              </div>
            )}

            {situation.debitos && (
              <div className="border-t border-border/30 pt-2">
                <span className="text-xs font-semibold text-red-500 block uppercase tracking-wider">
                  Débitos Fiscais Ativos
                </span>
                <ul className="list-disc pl-4 text-xs space-y-1 mt-1 text-muted-foreground">
                  {Array.isArray(situation.debitos) ? (
                    situation.debitos.map((d, idx) => <li key={idx}>{d}</li>)
                  ) : (
                    <li>{String(situation.debitos)}</li>
                  )}
                </ul>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
