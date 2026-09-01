import { Lock, Zap } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Card, CardContent } from '@/components/ui/Card';
import { cn } from '@/lib/utils';
import type { SubscriptionPlan } from '@/lib/hooks/useCalculator';
import { PLAN_INFO } from '@/lib/hooks/useCalculator';

interface PlanGateProps {
  requiredPlan: Exclude<SubscriptionPlan, 'free'>;
  currentPlan: SubscriptionPlan;
  children: React.ReactNode;
  inline?: boolean;
}

export function PlanGate({ requiredPlan, currentPlan, children, inline = false }: PlanGateProps) {
  const planOrder: SubscriptionPlan[] = ['free', 'intermediario', 'premium'];
  const currentIndex = planOrder.indexOf(currentPlan);
  const requiredIndex = planOrder.indexOf(requiredPlan);
  const hasAccess = currentIndex >= requiredIndex;

  if (hasAccess) return <>{children}</>;

  const plan = PLAN_INFO[requiredPlan];

  if (inline) {
    return (
      <div className="flex items-center gap-3 rounded-lg border border-dashed border-muted-foreground/30 bg-muted/30 px-4 py-3">
        <Lock className="h-4 w-4 shrink-0 text-muted-foreground" aria-hidden="true" />
        <p className="flex-1 text-sm text-muted-foreground">
          Disponível no plano{' '}
          <span className="font-semibold text-foreground">{plan.label}</span>
          {plan.price !== null && (
            <span className="text-muted-foreground"> — R$ {plan.price}/mês</span>
          )}
        </p>
        <Button
          size="sm"
          variant="outline"
          className="shrink-0 border-primary/40 text-primary hover:bg-primary/10"
          onClick={() => window.location.href = '/financeiro'}
          aria-label={`Fazer upgrade para o plano ${plan.label}`}
        >
          <Zap className="h-3.5 w-3.5" aria-hidden="true" />
          Upgrade
        </Button>
      </div>
    );
  }

  return (
    <Card className="border-dashed border-muted-foreground/30">
      <CardContent className="flex flex-col items-center gap-4 px-6 py-12 text-center">
        <div
          className={cn(
            'flex h-14 w-14 items-center justify-center rounded-full',
            'bg-muted text-muted-foreground',
          )}
        >
          <Lock className="h-6 w-6" aria-hidden="true" />
        </div>
        <div className="space-y-1">
          <p className="font-semibold text-foreground">
            Disponível no plano {plan.label}
          </p>
          {plan.price !== null && (
            <p className="text-sm text-muted-foreground">
              A partir de R$ {plan.price}/mês
            </p>
          )}
        </div>
        <ul className="space-y-1.5 text-left text-sm text-muted-foreground">
          {plan.features.map((f) => (
            <li key={f} className="flex items-center gap-2">
              <span className="h-1.5 w-1.5 rounded-full bg-primary" aria-hidden="true" />
              {f}
            </li>
          ))}
        </ul>
        <Button
          onClick={() => window.location.href = '/financeiro'}
          className="mt-2"
          aria-label={`Fazer upgrade para o plano ${plan.label}`}
        >
          <Zap className="h-4 w-4" aria-hidden="true" />
          Fazer Upgrade
        </Button>
      </CardContent>
    </Card>
  );
}
