import { useState } from 'react';
import toast from 'react-hot-toast';
import {
  History,
  BarChart3,
  Building2,
  TrendingUp,
  FileDown,
  Eye,
  Calendar,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Dialog } from '@/components/ui/Dialog';
import { EmptyState, ErrorState, PageSpinner } from '@/components/ui/StateViews';
import { PlanGate } from './PlanGate';
import {
  useSimulationHistory,
  moneyBRL,
  planHasPDF,
  type SubscriptionPlan,
  type SavedSimulation,
  type SimulationType,
} from '@/lib/hooks/useCalculator';

interface HistoryTabProps {
  plan: SubscriptionPlan;
}

const SIM_ICONS: Record<SimulationType, React.ElementType> = {
  regime: BarChart3,
  icms: Building2,
  pis_cofins: TrendingUp,
};

const SIM_LABELS: Record<SimulationType, string> = {
  regime: 'Regime Tributário',
  icms: 'ICMS',
  pis_cofins: 'PIS/COFINS',
};

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('pt-BR', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function SimulationDetail({ sim }: { sim: SavedSimulation }) {
  const r = sim.result;
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-3">
        <div className="rounded-lg bg-muted/50 p-3">
          <p className="text-xs text-muted-foreground">Receita bruta</p>
          <p className="text-sm font-semibold">{moneyBRL(sim.gross_revenue)}</p>
        </div>
        <div className="rounded-lg bg-muted/50 p-3">
          <p className="text-xs text-muted-foreground">Custos</p>
          <p className="text-sm font-semibold">{moneyBRL(sim.costs)}</p>
        </div>
        <div className="rounded-lg bg-muted/50 p-3">
          <p className="text-xs text-muted-foreground">Setor</p>
          <p className="text-sm font-semibold capitalize">{sim.sector}</p>
        </div>
        <div className="rounded-lg bg-muted/50 p-3">
          <p className="text-xs text-muted-foreground">Estado</p>
          <p className="text-sm font-semibold">{sim.region}</p>
        </div>
      </div>

      {r.simulation_type === 'regime' && r.regime_options && (
        <div className="space-y-2">
          <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Comparativo de regimes
          </p>
          {r.regime_options.map((opt) => (
            <div
              key={opt.regime}
              className="flex justify-between rounded-lg border border-border bg-muted/30 p-3"
            >
              <span className="text-sm">{opt.label ?? opt.regime}</span>
              <span className="text-sm font-semibold">{moneyBRL(opt.tax_amount)}</span>
            </div>
          ))}
        </div>
      )}

      {r.simulation_type === 'icms' && r.icms_result && (
        <div className="space-y-2">
          <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            ICMS
          </p>
          <div className="flex justify-between rounded-lg border border-border bg-muted/30 p-3">
            <span className="text-sm">Alíquota</span>
            <span className="text-sm font-semibold">{r.icms_result.rate}%</span>
          </div>
          <div className="flex justify-between rounded-lg border border-primary/30 bg-primary/5 p-3">
            <span className="text-sm font-medium">Imposto</span>
            <span className="text-sm font-bold text-primary">
              {moneyBRL(r.icms_result.tax_amount)}
            </span>
          </div>
        </div>
      )}

      {r.simulation_type === 'pis_cofins' && r.pis_cofins_result && (
        <div className="space-y-2">
          <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            PIS/COFINS
          </p>
          <div className="flex justify-between rounded-lg border border-border bg-muted/30 p-3">
            <span className="text-sm">PIS</span>
            <span className="text-sm font-semibold">
              {moneyBRL(r.pis_cofins_result.pis_amount)}
            </span>
          </div>
          <div className="flex justify-between rounded-lg border border-border bg-muted/30 p-3">
            <span className="text-sm">COFINS</span>
            <span className="text-sm font-semibold">
              {moneyBRL(r.pis_cofins_result.cofins_amount)}
            </span>
          </div>
          <div className="flex justify-between rounded-lg border border-primary/30 bg-primary/5 p-3">
            <span className="text-sm font-medium">Total</span>
            <span className="text-sm font-bold text-primary">
              {moneyBRL(r.pis_cofins_result.total_amount)}
            </span>
          </div>
        </div>
      )}

      {r.ai_recommendation && (
        <div className="rounded-lg border border-amber-500/20 bg-amber-500/5 p-4">
          <p className="mb-1 text-xs font-semibold text-amber-400">Recomendação IA</p>
          <p className="text-sm leading-relaxed">{r.ai_recommendation}</p>
        </div>
      )}
    </div>
  );
}

export function HistoryTab({ plan }: HistoryTabProps) {
  const { data: history, isLoading, isError } = useSimulationHistory();
  const [selected, setSelected] = useState<SavedSimulation | null>(null);
  const hasPDF = planHasPDF(plan);

  if (isLoading) return <PageSpinner />;
  if (isError) return <ErrorState message="Não foi possível carregar o histórico de simulações." />;
  if (!history?.length) {
    return (
      <EmptyState
        title="Nenhuma simulação salva"
        description="Execute uma simulação e clique em Salvar para guardar no histórico."
      />
    );
  }

  return (
    <>
      <div className="space-y-3" role="list" aria-label="Histórico de simulações">
        {history.map((sim) => {
          const Icon = SIM_ICONS[sim.simulation_type];
          return (
            <Card
              key={sim.id}
              role="listitem"
              className="transition-all hover:border-primary/30 hover:shadow-glow-sm"
            >
              <CardContent className="flex items-center gap-4 py-4">
                <div
                  className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-muted"
                  aria-hidden="true"
                >
                  <Icon className="h-5 w-5 text-muted-foreground" />
                </div>

                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <p className="text-sm font-semibold">
                      {SIM_LABELS[sim.simulation_type]}
                    </p>
                    <Badge variant="info" className="hidden sm:inline-flex">
                      {sim.region}
                    </Badge>
                  </div>
                  <div className="mt-0.5 flex items-center gap-3 text-xs text-muted-foreground">
                    <span className="flex items-center gap-1">
                      <Calendar className="h-3 w-3" aria-hidden="true" />
                      {formatDate(sim.created_at)}
                    </span>
                    <span>Receita: {moneyBRL(sim.gross_revenue)}</span>
                  </div>
                </div>

                <div className="flex shrink-0 gap-2">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => setSelected(sim)}
                    aria-label={`Visualizar simulação de ${SIM_LABELS[sim.simulation_type]}`}
                  >
                    <Eye className="h-3.5 w-3.5" aria-hidden="true" />
                    <span className="hidden sm:inline">Ver</span>
                  </Button>

                  {hasPDF ? (
                    <Button
                      size="sm"
                      variant="outline"
                      aria-label="Exportar como PDF"
                      onClick={() => toast('Exportação de PDF em breve!', { icon: '📄' })}
                    >
                      <FileDown className="h-3.5 w-3.5" aria-hidden="true" />
                      <span className="hidden sm:inline">PDF</span>
                    </Button>
                  ) : null}
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* PDF gate for non-premium */}
      {!hasPDF && (
        <div className="mt-4">
          <PlanGate requiredPlan="premium" currentPlan={plan} inline>
            <span />
          </PlanGate>
        </div>
      )}

      {/* Detail dialog */}
      <Dialog
        open={!!selected}
        onClose={() => setSelected(null)}
        title={selected ? `${SIM_LABELS[selected.simulation_type]} — ${formatDate(selected.created_at)}` : ''}
      >
        {selected && <SimulationDetail sim={selected} />}
      </Dialog>
    </>
  );
}
