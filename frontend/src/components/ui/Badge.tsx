import { HTMLAttributes } from 'react';
import { cn } from '@/lib/utils';

interface BadgeProps extends HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'success' | 'warning' | 'error' | 'info';
}

export function Badge({ className, variant = 'default', ...props }: BadgeProps) {
  return (
    <div
      className={cn(
        'inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-semibold transition-colors',
        {
          'border-primary/25 bg-primary/10 text-primary dark:border-primary/35 dark:bg-primary/15': variant === 'default',
          'border-emerald-500/25 bg-emerald-500/10 text-emerald-700 dark:border-emerald-400/25 dark:bg-emerald-500/10 dark:text-emerald-300': variant === 'success',
          'border-amber-500/25 bg-amber-500/10 text-amber-700 dark:border-amber-400/25 dark:bg-amber-500/10 dark:text-amber-300': variant === 'warning',
          'border-red-500/25 bg-red-500/10 text-red-700 dark:border-red-400/25 dark:bg-red-500/10 dark:text-red-300': variant === 'error',
          'border-sky-500/25 bg-sky-500/10 text-sky-700 dark:border-sky-400/25 dark:bg-sky-500/10 dark:text-sky-300': variant === 'info',
        },
        className
      )}
      {...props}
    />
  );
}
