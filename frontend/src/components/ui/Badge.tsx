import { HTMLAttributes } from 'react';
import { cn } from '@/lib/utils';

export type BadgeVariant =
  | 'default'
  | 'success'
  | 'warning'
  | 'error'
  | 'info'
  | 'regular'
  | 'attention'
  | 'critical'
  | 'pending'
  | 'completed'
  | 'overdue'
  | 'paid'
  | 'expiring';

interface BadgeProps extends HTMLAttributes<HTMLDivElement> {
  variant?: BadgeVariant;
}

export function Badge({ className, variant = 'default', ...props }: BadgeProps) {
  return (
    <div
      className={cn(
        'inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-semibold transition-all duration-150 select-none',
        {
          // Legacy mappings
          'border-primary/25 bg-primary/10 text-primary dark:border-primary/35 dark:bg-primary/15': variant === 'default',
          'border-success/25 bg-success/10 text-success dark:border-success/25 dark:bg-success/10 dark:text-success': variant === 'success' || variant === 'completed' || variant === 'paid',
          'border-warning/25 bg-warning/10 text-warning dark:border-warning/25 dark:bg-warning/10 dark:text-warning': variant === 'warning' || variant === 'attention' || variant === 'expiring',
          'border-destructive/25 bg-destructive/10 text-destructive dark:border-destructive/25 dark:bg-destructive/10 dark:text-destructive': variant === 'error' || variant === 'critical' || variant === 'overdue',
          'border-info/25 bg-info/10 text-info dark:border-info/25 dark:bg-info/10 dark:text-info': variant === 'info' || variant === 'regular' || variant === 'pending',
        },
        className
      )}
      {...props}
    />
  );
}

