import { Crown, Star, Zap } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { SubscriptionPlan } from '@/lib/hooks/useCalculator';
import { PLAN_INFO } from '@/lib/hooks/useCalculator';

interface PlanBadgeProps {
  plan: SubscriptionPlan;
  className?: string;
}

const PLAN_ICONS: Record<SubscriptionPlan, React.ElementType> = {
  free: Zap,
  intermediario: Star,
  premium: Crown,
};

const PLAN_STYLES: Record<SubscriptionPlan, string> = {
  free: 'bg-muted text-muted-foreground border-muted-foreground/20',
  intermediario: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
  premium: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
};

export function PlanBadge({ plan, className }: PlanBadgeProps) {
  const Icon = PLAN_ICONS[plan];
  const info = PLAN_INFO[plan];

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs font-semibold',
        PLAN_STYLES[plan],
        className,
      )}
      aria-label={`Plano atual: ${info.label}`}
    >
      <Icon className="h-3 w-3" aria-hidden="true" />
      {info.label}
    </span>
  );
}
