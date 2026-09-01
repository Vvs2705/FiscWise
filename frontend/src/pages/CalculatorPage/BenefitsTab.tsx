import { MapPin, TrendingDown, CheckCircle2, Clock } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { ErrorState, PageSpinner } from '@/components/ui/StateViews';
import { PlanGate } from './PlanGate';
import {
  useFiscalBenefits,
  moneyBRL,
  planHasBenefits,
  type SubscriptionPlan,
  type BenefitStatus,
  type FiscalBenefit,
} from '@/lib/hooks/useCalculator';
import { cn } from '@/lib/utils';

interface BenefitsTabProps {
  plan: SubscriptionPlan;
}

const STATUS_CONFIG: Record<BenefitStatus, { label: string; icon: React.ElementType; badge: 'success' | 'warning' }> = {
  applied: { label: 'Aplicado', icon: CheckCircle2, badge: 'success' },
  pending: { label: 'Pendente', icon: Clock, badge: 'warning' },
};

function BenefitCard({ benefit }: { benefit: FiscalBenefit }) {
  const status = STATUS_CONFIG[benefit.status];
  const StatusIcon = status.icon;

  return (
    <Card className="transition-all hover:border-primary/30 hover:shadow-glow-sm">
      <CardContent className="py-4">
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <p className="text-sm font-semibold">{benefit.name}</p>
              <Badge variant={status.badge} className="flex items-center gap-1">
                <StatusIcon className="h-3 w-3" aria-hidden="true" />
                {status.label}
              </Badge>
            </div>
            <p className="mt-1 text-xs text-muted-foreground">{benefit.description}</p>
            <div className="mt-2 flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
              <span className="flex items-center gap-1">
                <MapPin className="h-3 w-3" aria-hidden="true" />
                {benefit.state === 'all' ? 'Todo o Brasil' : benefit.state}
              </span>
              {benefit.regime !== 'all' && (
                <span className="rounded-full bg-muted px-2 py-0.5 capitalize">
                  {benefit.regime.replace('_', ' ')}
                </span>
              )}
            </div>
          </div>
          <div
            className={cn(
              'shrink-0 rounded-lg border px-3 py-2 text-right',
              benefit.status === 'applied'
                ? 'border-green-500/20 bg-green-500/5'
                : 'border-muted bg-muted/30',
            )}
          >
            <div className="flex items-center gap-1 text-xs text-muted-foreground">
              <TrendingDown className="h-3 w-3" aria-hidden="true" />
              Economia estimada
            </div>
            <p
              className={cn(
                'text-sm font-bold',
                benefit.status === 'applied' ? 'text-green-400' : 'text-foreground',
              )}
            >
              {moneyBRL(benefit.estimated_savings)}/mês
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function BenefitsContent() {
  const { data: benefits, isLoading, isError } = useFiscalBenefits();

  if (isLoading) return <PageSpinner />;
  if (isError) return <ErrorState message="Não foi possível carregar os benefícios fiscais." />;

  const applied = benefits?.filter((b) => b.status === 'applied') ?? [];
  const pending = benefits?.filter((b) => b.status === 'pending') ?? [];
  const totalSavings = applied.reduce((acc, b) => acc + b.estimated_savings, 0);

  return (
    <div className="space-y-6">
      {/* Summary card */}
      {applied.length > 0 && (
        <Card className="border-green-500/20 bg-green-500/5">
          <CardContent className="flex items-center justify-between py-4">
            <div className="flex items-center gap-3">
              <CheckCircle2 className="h-5 w-5 text-green-400" aria-hidden="true" />
              <div>
                <p className="text-sm font-semibold text-green-400">
                  {applied.length} benefício{applied.length !== 1 ? 's' : ''} aplicado{applied.length !== 1 ? 's' : ''}
                </p>
                <p className="text-xs text-muted-foreground">
                  Economia total estimada
                </p>
              </div>
            </div>
            <p className="text-lg font-bold text-green-400">
              {moneyBRL(totalSavings)}/mês
            </p>
          </CardContent>
        </Card>
      )}

      {/* Applied benefits */}
      {applied.length > 0 && (
        <section aria-label="Benefícios aplicados">
          <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold text-muted-foreground">
            <CheckCircle2 className="h-4 w-4 text-green-400" aria-hidden="true" />
            Aplicados ({applied.length})
          </h3>
          <div className="space-y-3">
            {applied.map((b) => <BenefitCard key={b.id} benefit={b} />)}
          </div>
        </section>
      )}

      {/* Pending benefits */}
      {pending.length > 0 && (
        <section aria-label="Benefícios pendentes">
          <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold text-muted-foreground">
            <Clock className="h-4 w-4 text-yellow-500" aria-hidden="true" />
            Pendentes ({pending.length})
          </h3>
          <div className="space-y-3">
            {pending.map((b) => <BenefitCard key={b.id} benefit={b} />)}
          </div>
        </section>
      )}

      {!benefits?.length && (
        <div className="flex flex-col items-center justify-center py-12 text-center">
          <TrendingDown className="mb-3 h-10 w-10 text-muted-foreground/40" aria-hidden="true" />
          <p className="font-medium">Nenhum benefício encontrado</p>
          <p className="mt-1 text-sm text-muted-foreground">
            Execute simulações para identificar benefícios disponíveis para seu perfil.
          </p>
        </div>
      )}
    </div>
  );
}

export function BenefitsTab({ plan }: BenefitsTabProps) {
  const hasBenefits = planHasBenefits(plan);

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-base">
            <TrendingDown className="h-4 w-4 text-primary" aria-hidden="true" />
            Benefícios Fiscais por Estado
          </CardTitle>
          <p className="text-sm text-muted-foreground">
            Incentivos e isenções disponíveis para seu perfil tributário.
          </p>
        </CardHeader>
      </Card>

      {hasBenefits ? (
        <BenefitsContent />
      ) : (
        <PlanGate requiredPlan="premium" currentPlan={plan}>
          <span />
        </PlanGate>
      )}
    </div>
  );
}
