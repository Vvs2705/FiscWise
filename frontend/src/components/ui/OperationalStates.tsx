import { ReactNode } from 'react';
import { Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';

// ─── LoadingState ───────────────────────────────────────────────────────────

interface LoadingStateProps {
  message?: string;
  className?: string;
}

export function LoadingState({ message = 'Carregando...', className }: LoadingStateProps) {
  return (
    <div role="status" className={cn('flex flex-col items-center justify-center gap-3 py-16 text-center', className)}>
      <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" aria-hidden="true" />
      <p className="text-sm text-muted-foreground">{message}</p>
    </div>
  );
}

// ─── EmptyState / ErrorState / SkeletonTable ───────────────────────────────
// Componentes únicos, reexportados para manter os imports antigos.

export { EmptyState } from './EmptyState';
export { ErrorState } from './ErrorState';
export { SkeletonTable } from './LoadingSkeleton';

// ─── MetricCard ─────────────────────────────────────────────────────────────

interface MetricCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon?: ReactNode;
  trend?: { value: number; label: string };
  variant?: 'default' | 'success' | 'warning' | 'danger';
  className?: string;
}

const METRIC_VARIANTS = {
  default: 'border-border',
  success: 'border-success/25',
  warning: 'border-warning/25',
  danger: 'border-destructive/25',
};

export function MetricCard({ title, value, subtitle, icon, trend, variant = 'default', className }: MetricCardProps) {
  return (
    <div className={cn('rounded-lg border bg-card p-4 sm:p-5', METRIC_VARIANTS[variant], className)}>
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <p className="text-xs font-medium text-muted-foreground">{title}</p>
          <p className="mt-1 text-2xl font-semibold tabular-nums tracking-tight text-foreground">{value}</p>
          {subtitle && <p className="mt-0.5 text-xs text-muted-foreground">{subtitle}</p>}
          {trend && (
            <p className={cn('mt-1 text-xs font-medium tabular-nums', trend.value >= 0 ? 'text-success' : 'text-destructive')}>
              {trend.value >= 0 ? '+' : ''}{trend.value}% {trend.label}
            </p>
          )}
        </div>
        {icon && (
          <div className="ml-3 flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-muted text-muted-foreground">
            {icon}
          </div>
        )}
      </div>
    </div>
  );
}

// ─── ActionCard ─────────────────────────────────────────────────────────────

interface ActionCardProps {
  title: string;
  description?: string;
  icon?: ReactNode;
  onClick?: () => void;
  badge?: string;
  disabled?: boolean;
  className?: string;
}

export function ActionCard({ title, description, icon, onClick, badge, disabled, className }: ActionCardProps) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={cn(
        'group flex w-full items-start gap-3 rounded-lg border border-border bg-card p-4 text-left',
        'transition-[border-color,box-shadow] duration-150 ease-out hover:border-primary/40 hover:shadow-md',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
        disabled && 'cursor-not-allowed opacity-50',
        className,
      )}
    >
      {icon && (
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-muted text-muted-foreground transition-colors duration-150 group-hover:bg-primary/10 group-hover:text-primary">
          {icon}
        </div>
      )}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-foreground">{title}</span>
          {badge && (
            <span className="rounded-sm border border-primary/25 bg-primary/10 px-1.5 py-0.5 text-xs font-medium text-primary">
              {badge}
            </span>
          )}
        </div>
        {description && <p className="mt-0.5 text-xs text-muted-foreground">{description}</p>}
      </div>
    </button>
  );
}

// ─── WarningPanel ───────────────────────────────────────────────────────────

interface WarningPanelProps {
  title: string;
  description?: string;
  children?: ReactNode;
  variant?: 'warning' | 'danger' | 'info';
  className?: string;
}

const WARNING_VARIANTS = {
  warning: 'border-warning/25 bg-warning/10 text-warning',
  danger: 'border-destructive/25 bg-destructive/10 text-destructive',
  info: 'border-info/25 bg-info/10 text-info',
};

export function WarningPanel({ title, description, children, variant = 'warning', className }: WarningPanelProps) {
  return (
    <div className={cn('rounded-lg border p-4', WARNING_VARIANTS[variant], className)}>
      <p className="text-sm font-medium">{title}</p>
      {description && <p className="mt-1 text-sm text-foreground/80">{description}</p>}
      {children}
    </div>
  );
}

// ─── SimulationNotice ───────────────────────────────────────────────────────

/** Aviso fixo para telas cujo provedor externo ainda é simulado. */
export function SimulationNotice({ children }: { children: ReactNode }) {
  return (
    <div
      role="note"
      className="rounded-lg border border-warning/25 bg-warning/10 px-4 py-3 text-sm text-foreground"
    >
      <strong className="font-semibold">Modo de demonstração.</strong> {children}
    </div>
  );
}
