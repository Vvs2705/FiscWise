import { HTMLAttributes, forwardRef } from 'react';
import { LucideIcon, ArrowUpRight, ArrowDownRight, FileText, CheckCircle2, ShieldAlert } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface CardProps extends HTMLAttributes<HTMLDivElement> {
  /** Card clicável: borda e sombra média no hover, foco visível. */
  interactive?: boolean;
}

export const Card = forwardRef<HTMLDivElement, CardProps>(
  ({ className, interactive = false, ...props }, ref) => (
    <div
      ref={ref}
      className={cn(
        'rounded-lg border border-border bg-card text-card-foreground',
        interactive &&
          'cursor-pointer transition-[border-color,box-shadow] duration-150 ease-out hover:border-primary/40 hover:shadow-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
        className,
      )}
      {...props}
    />
  ),
);
Card.displayName = 'Card';

export const CardHeader = forwardRef<HTMLDivElement, HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn('flex flex-col space-y-1.5 p-4 sm:p-5', className)} {...props} />
  ),
);
CardHeader.displayName = 'CardHeader';

export const CardTitle = forwardRef<HTMLParagraphElement, HTMLAttributes<HTMLHeadingElement>>(
  ({ className, ...props }, ref) => (
    <h3
      ref={ref}
      className={cn('text-base font-semibold leading-6 text-foreground', className)}
      {...props}
    />
  ),
);
CardTitle.displayName = 'CardTitle';

export const CardDescription = forwardRef<
  HTMLParagraphElement,
  HTMLAttributes<HTMLParagraphElement>
>(({ className, ...props }, ref) => (
  <p ref={ref} className={cn('text-sm text-muted-foreground', className)} {...props} />
));
CardDescription.displayName = 'CardDescription';

export const CardContent = forwardRef<HTMLDivElement, HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn('p-4 pt-0 sm:p-5 sm:pt-0', className)} {...props} />
  ),
);
CardContent.displayName = 'CardContent';

export const CardFooter = forwardRef<HTMLDivElement, HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn('flex items-center p-4 pt-0 sm:p-5 sm:pt-0', className)} {...props} />
  ),
);
CardFooter.displayName = 'CardFooter';

// ─── Metric Card ─────────────────────────────────────────────────────────────
interface MetricCardProps extends HTMLAttributes<HTMLDivElement> {
  title: string;
  value: string | number;
  detail?: string;
  icon?: LucideIcon;
  trend?: {
    value: number;
    isPositive: boolean;
    label?: string;
  };
}

export const MetricCard = forwardRef<HTMLDivElement, MetricCardProps>(
  ({ className, title, value, detail, icon: Icon, trend, ...props }, ref) => (
    <Card ref={ref} className={cn('relative overflow-hidden p-5', className)} {...props}>
      <div className="flex justify-between items-start mb-4">
        <span className="text-sm font-medium text-muted-foreground">{title}</span>
        {Icon && (
          <div className="flex h-9 w-9 items-center justify-center rounded-md bg-primary/10 text-primary">
            <Icon className="h-[18px] w-[18px]" aria-hidden="true" />
          </div>
        )}
      </div>
      <div>
        <p className="mb-1 text-2xl font-semibold tabular-nums tracking-tight text-foreground">{value}</p>
        <div className="flex items-center gap-2">
          {trend && (
            <span
              className={cn(
                'inline-flex items-center gap-0.5 rounded-sm border px-1.5 py-0.5 text-xs font-medium tabular-nums',
                trend.isPositive
                  ? 'border-success/25 bg-success/10 text-success'
                  : 'border-destructive/25 bg-destructive/10 text-destructive'
              )}
            >
              {trend.isPositive ? <ArrowUpRight className="w-3.5 h-3.5" /> : <ArrowDownRight className="w-3.5 h-3.5" />}
              {trend.value}%
            </span>
          )}
          {detail && <span className="text-xs text-muted-foreground">{detail}</span>}
        </div>
      </div>
    </Card>
  )
);
MetricCard.displayName = 'MetricCard';

// ─── Action Card ─────────────────────────────────────────────────────────────
interface ActionCardProps extends HTMLAttributes<HTMLDivElement> {
  title: string;
  description: string;
  icon: LucideIcon;
  onClick?: () => void;
  ctaText?: string;
}

export const ActionCard = forwardRef<HTMLDivElement, ActionCardProps>(
  ({ className, title, description, icon: Icon, onClick, ctaText = 'Acessar', ...props }, ref) => (
    <Card
      ref={ref}
      onClick={onClick}
      interactive
      className={cn('group p-5', className)}
      {...props}
    >
      <div className="mb-4 flex h-10 w-10 items-center justify-center rounded-md bg-primary/10 text-primary">
        <Icon className="h-5 w-5" aria-hidden="true" />
      </div>
      <h3 className="mb-1 text-base font-semibold text-foreground">{title}</h3>
      <p className="text-sm text-muted-foreground mb-4 line-clamp-2">{description}</p>
      <span className="inline-flex items-center gap-1 text-sm font-medium text-primary group-hover:underline underline-offset-4">
        {ctaText} →
      </span>
    </Card>
  )
);
ActionCard.displayName = 'ActionCard';

// ─── Risk Card ───────────────────────────────────────────────────────────────
interface RiskFactor {
  label: string;
  impact: number;
  status: 'critical' | 'warning' | 'info';
}

interface RiskCardProps extends HTMLAttributes<HTMLDivElement> {
  score: number;
  label: string;
  factors: RiskFactor[];
}

export const RiskCard = forwardRef<HTMLDivElement, RiskCardProps>(
  ({ className, score, label, factors, ...props }, ref) => {
    const ringColor =
      score >= 90
        ? 'text-success'
        : score >= 75
        ? 'text-info'
        : score >= 55
        ? 'text-warning'
        : 'text-destructive';

    return (
      <Card ref={ref} className={cn('p-5', className)} {...props}>
        <div className="flex items-center gap-4 mb-6">
          {/* Circular Progress Ring */}
          <div className="relative w-16 h-16 flex-shrink-0">
            <svg className="w-full h-full transform -rotate-90" viewBox="0 0 36 36">
              <path
                className="text-muted"
                strokeWidth="3.5"
                stroke="currentColor"
                fill="none"
                d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
              />
              <path
                className={cn('transition-[stroke-dasharray] duration-200 ease-out', ringColor)}
                strokeWidth="3.5"
                strokeDasharray={`${score}, 100`}
                strokeLinecap="round"
                stroke="currentColor"
                fill="none"
                d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
              />
            </svg>
            <div className="absolute inset-0 flex items-center justify-center font-semibold text-base tabular-nums text-foreground">
              {score}
            </div>
          </div>
          <div>
            <h3 className="text-base font-semibold text-foreground">{label}</h3>
            <p className="text-xs text-muted-foreground">Score de saúde da carteira</p>
          </div>
        </div>

        {factors.length > 0 ? (
          <div className="space-y-3">
            {factors.map((factor, index) => (
              <div key={index} className="flex justify-between items-center text-xs">
                <span className="text-muted-foreground flex items-center gap-1.5">
                  <span
                    className={cn(
                      'w-2 h-2 rounded-full',
                      factor.status === 'critical'
                        ? 'bg-destructive'
                        : factor.status === 'warning'
                        ? 'bg-warning'
                        : 'bg-info'
                    )}
                  />
                  {factor.label}
                </span>
                <span className="font-medium tabular-nums text-foreground">{factor.impact} pts</span>
              </div>
            ))}
          </div>
        ) : (
          <div className="flex items-center gap-2 p-3 rounded-md border border-success/25 bg-success/10 text-xs text-success">
            <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
            <span>Nenhum fator de risco ativo. Parabéns!</span>
          </div>
        )}
      </Card>
    );
  }
);
RiskCard.displayName = 'RiskCard';

// ─── Document Card ───────────────────────────────────────────────────────────
interface DocumentCardProps extends HTMLAttributes<HTMLDivElement> {
  name: string;
  type: string;
  date: string;
  status: 'available' | 'missing' | 'expired' | 'review';
  onClick?: () => void;
}

export const DocumentCard = forwardRef<HTMLDivElement, DocumentCardProps>(
  ({ className, name, type, date, status, onClick, ...props }, ref) => {
    const statusConfig = {
      available: { label: 'Disponível', color: 'text-success border-success/25 bg-success/10' },
      missing: { label: 'Pendente', color: 'text-warning border-warning/25 bg-warning/10' },
      expired: { label: 'Expirado', color: 'text-destructive border-destructive/25 bg-destructive/10' },
      review: { label: 'Em revisão', color: 'text-info border-info/25 bg-info/10' },
    };

    const config = statusConfig[status];

    return (
      <Card
        ref={ref}
        onClick={onClick}
        interactive
        className={cn('group flex items-center justify-between p-4', className)}
        {...props}
      >
        <div className="flex items-center gap-3 min-w-0">
          <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-md bg-muted text-muted-foreground transition-colors duration-150 group-hover:text-primary">
            <FileText className="w-5 h-5" />
          </div>
          <div className="min-w-0">
            <h4 className="text-sm font-semibold text-foreground truncate">{name}</h4>
            <p className="text-xs text-muted-foreground truncate">{type}</p>
          </div>
        </div>
        <div className="flex flex-col items-end gap-1.5 flex-shrink-0">
          <span className={cn('rounded-sm border px-2 py-0.5 text-xs font-medium', config.color)}>
            {config.label}
          </span>
          <span className="text-xs tabular-nums text-muted-foreground">{date}</span>
        </div>
      </Card>
    );
  }
);
DocumentCard.displayName = 'DocumentCard';

// ─── Certificate Card ────────────────────────────────────────────────────────
interface CertificateCardProps extends HTMLAttributes<HTMLDivElement> {
  label: string;
  type: string;
  expiryDate: string;
  daysRemaining: number;
  onWarnClient?: (e: React.MouseEvent) => void;
}

export const CertificateCard = forwardRef<HTMLDivElement, CertificateCardProps>(
  ({ className, label, type, expiryDate, daysRemaining, onWarnClient, ...props }, ref) => {
    const isCritical = daysRemaining <= 15;
    const isWarning = daysRemaining <= 30 && daysRemaining > 15;

    return (
      <Card ref={ref} className={cn('relative p-5', className)} {...props}>
        <div className="flex items-start justify-between mb-4">
          <div>
            <span className="mb-1 block text-xs font-medium text-muted-foreground">
              Certificado {type}
            </span>
            <h4 className="text-base font-semibold leading-tight text-foreground">{label}</h4>
          </div>
          {(isCritical || isWarning) && (
            <div className={cn('rounded-md p-1.5', isCritical ? 'bg-destructive/10 text-destructive' : 'bg-warning/10 text-warning')}>
              <ShieldAlert className="w-5 h-5" />
            </div>
          )}
        </div>

        <div className="mb-4">
          <div className="flex justify-between items-center text-xs mb-1">
            <span className="text-muted-foreground">Validade: {expiryDate}</span>
            <span className={cn('font-medium tabular-nums', isCritical ? 'text-destructive' : isWarning ? 'text-warning' : 'text-success')}>
              {daysRemaining} dias restantes
            </span>
          </div>
          {/* Progress bar */}
          <div className="h-1.5 bg-muted rounded-full overflow-hidden">
            <div
              className={cn(
                'h-full rounded-full',
                isCritical ? 'bg-destructive' : isWarning ? 'bg-warning' : 'bg-success'
              )}
              style={{ width: `${Math.min(100, (daysRemaining / 365) * 100)}%` }}
            />
          </div>
        </div>

        {onWarnClient && (isCritical || isWarning) && (
          <button
            onClick={onWarnClient}
            className="h-9 w-full rounded-md border border-primary/25 bg-primary/10 text-sm font-medium text-primary transition-colors duration-100 hover:bg-primary/15 active:scale-[0.98] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            Avisar cliente
          </button>
        )}
      </Card>
    );
  }
);
CertificateCard.displayName = 'CertificateCard';

