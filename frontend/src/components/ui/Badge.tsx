import { HTMLAttributes } from 'react';
import { cn } from '@/lib/utils';

export type BadgeVariant =
  // DESIGN.md §8
  | 'neutral'
  | 'primary'
  | 'success'
  | 'warning'
  | 'danger'
  | 'info'
  // Aliases legados
  | 'default'
  | 'error'
  | 'regular'
  | 'attention'
  | 'critical'
  | 'pending'
  | 'completed'
  | 'overdue'
  | 'paid'
  | 'expiring';

/** Status sempre com fundo /10, borda /25 e texto na cor cheia. */
export const BADGE_TONES = {
  neutral: 'border-border bg-muted text-muted-foreground',
  primary: 'border-primary/25 bg-primary/10 text-primary',
  success: 'border-success/25 bg-success/10 text-success',
  warning: 'border-warning/25 bg-warning/10 text-warning',
  danger: 'border-destructive/25 bg-destructive/10 text-destructive',
  info: 'border-info/25 bg-info/10 text-info',
} as const;

export type BadgeTone = keyof typeof BADGE_TONES;

const VARIANT_TO_TONE: Record<BadgeVariant, BadgeTone> = {
  neutral: 'neutral',
  primary: 'primary',
  success: 'success',
  warning: 'warning',
  danger: 'danger',
  info: 'info',
  default: 'primary',
  error: 'danger',
  critical: 'danger',
  overdue: 'danger',
  attention: 'warning',
  expiring: 'warning',
  completed: 'success',
  paid: 'success',
  regular: 'info',
  pending: 'info',
};

interface BadgeProps extends HTMLAttributes<HTMLDivElement> {
  variant?: BadgeVariant;
}

export function Badge({ className, variant = 'default', ...props }: BadgeProps) {
  const tone = VARIANT_TO_TONE[variant] ?? 'neutral';
  return (
    <div
      className={cn(
        'inline-flex select-none items-center gap-1 whitespace-nowrap rounded-sm border px-2 py-0.5 text-xs font-medium',
        BADGE_TONES[tone],
        className,
      )}
      {...props}
    />
  );
}
