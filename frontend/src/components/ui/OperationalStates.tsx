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
    <div className={cn('flex flex-col items-center justify-center gap-3 py-16 text-center', className)}>
      <Loader2 className="h-8 w-8 animate-spin text-primary" />
      <p className="text-sm text-muted-foreground">{message}</p>
    </div>
  );
}

// ─── EmptyState ─────────────────────────────────────────────────────────────

interface EmptyStateProps {
  icon?: ReactNode;
  title: string;
  description?: string;
  action?: ReactNode;
  className?: string;
}

export function EmptyState({ icon, title, description, action, className }: EmptyStateProps) {
  return (
    <div className={cn('flex flex-col items-center justify-center gap-3 py-16 text-center', className)}>
      {icon && (
        <div className="flex h-12 w-12 items-center justify-center rounded-full bg-muted text-muted-foreground">
          {icon}
        </div>
      )}
      <div>
        <p className="text-sm font-medium text-foreground">{title}</p>
        {description && <p className="mt-1 text-xs text-muted-foreground max-w-sm">{description}</p>}
      </div>
      {action && <div className="mt-2">{action}</div>}
    </div>
  );
}

// ─── ErrorState ─────────────────────────────────────────────────────────────

interface ErrorStateProps {
  title?: string;
  description?: string;
  action?: ReactNode;
  className?: string;
}

export function ErrorState({
  title = 'Algo deu errado',
  description = 'Ocorreu um erro inesperado. Tente novamente.',
  action,
  className,
}: ErrorStateProps) {
  return (
    <div className={cn('flex flex-col items-center justify-center gap-3 py-16 text-center', className)}>
      <div className="flex h-12 w-12 items-center justify-center rounded-full bg-destructive/10 text-destructive">
        <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01M12 3a9 9 0 110 18A9 9 0 0112 3z" />
        </svg>
      </div>
      <div>
        <p className="text-sm font-medium text-foreground">{title}</p>
        <p className="mt-1 text-xs text-muted-foreground max-w-sm">{description}</p>
      </div>
      {action && <div className="mt-2">{action}</div>}
    </div>
  );
}

// ─── SkeletonTable ─────────────────────────────────────────────────────────

interface SkeletonTableProps {
  rows?: number;
  cols?: number;
  className?: string;
}

export function SkeletonTable({ rows = 5, cols = 4, className }: SkeletonTableProps) {
  return (
    <div className={cn('overflow-hidden rounded-lg border border-border', className)}>
      <div className="border-b border-border bg-muted/30 px-4 py-3">
        <div className="flex gap-4">
          {Array.from({ length: cols }).map((_, i) => (
            <div key={i} className="h-3 flex-1 animate-pulse rounded bg-muted" />
          ))}
        </div>
      </div>
      {Array.from({ length: rows }).map((_, row) => (
        <div key={row} className="flex gap-4 border-b border-border px-4 py-3.5 last:border-0">
          {Array.from({ length: cols }).map((_, col) => (
            <div
              key={col}
              className="h-3 flex-1 animate-pulse rounded bg-muted"
              style={{ opacity: 1 - row * 0.12 }}
            />
          ))}
        </div>
      ))}
    </div>
  );
}

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
  success: 'border-emerald-500/20 bg-emerald-500/5',
  warning: 'border-orange-500/20 bg-orange-500/5',
  danger: 'border-red-500/20 bg-red-500/5',
};

export function MetricCard({ title, value, subtitle, icon, trend, variant = 'default', className }: MetricCardProps) {
  return (
    <div className={cn('rounded-xl border bg-card p-4 transition-shadow hover:shadow-md', METRIC_VARIANTS[variant], className)}>
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <p className="text-xs font-medium text-muted-foreground">{title}</p>
          <p className="mt-1 text-2xl font-bold tabular-nums text-foreground">{value}</p>
          {subtitle && <p className="mt-0.5 text-xs text-muted-foreground">{subtitle}</p>}
          {trend && (
            <p className={cn('mt-1 text-xs font-medium', trend.value >= 0 ? 'text-emerald-400' : 'text-red-400')}>
              {trend.value >= 0 ? '+' : ''}{trend.value}% {trend.label}
            </p>
          )}
        </div>
        {icon && (
          <div className="ml-3 flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-muted text-muted-foreground">
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
        'group flex w-full items-start gap-3 rounded-xl border border-border bg-card p-4 text-left',
        'transition-all duration-150 hover:border-primary/40 hover:bg-primary/5 hover:shadow-sm',
        disabled && 'cursor-not-allowed opacity-50',
        className,
      )}
    >
      {icon && (
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-muted text-muted-foreground group-hover:bg-primary/10 group-hover:text-primary transition-colors">
          {icon}
        </div>
      )}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-foreground">{title}</span>
          {badge && (
            <span className="rounded-full bg-primary/10 px-1.5 py-0.5 text-[10px] font-semibold text-primary">
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
  warning: 'border-orange-500/30 bg-orange-500/5 text-orange-300',
  danger: 'border-red-500/30 bg-red-500/5 text-red-300',
  info: 'border-blue-500/30 bg-blue-500/5 text-blue-300',
};

export function WarningPanel({ title, description, children, variant = 'warning', className }: WarningPanelProps) {
  return (
    <div className={cn('rounded-lg border p-4', WARNING_VARIANTS[variant], className)}>
      <p className="text-sm font-medium">{title}</p>
      {description && <p className="mt-1 text-xs opacity-80">{description}</p>}
      {children}
    </div>
  );
}
