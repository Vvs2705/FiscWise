import { HTMLAttributes, forwardRef } from 'react';
import { LucideIcon, ArrowUpRight, ArrowDownRight, FileText, CheckCircle2, ShieldAlert } from 'lucide-react';
import { cn } from '@/lib/utils';

export const Card = forwardRef<HTMLDivElement, HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      className={cn(
        'fiscwise-surface rounded-2xl border border-border/70 bg-card/80 text-card-foreground',
        'transition-all duration-200 ease-out',
        className,
      )}
      {...props}
    />
  ),
);
Card.displayName = 'Card';

export const CardHeader = forwardRef<HTMLDivElement, HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn('flex flex-col space-y-1.5 p-6', className)} {...props} />
  ),
);
CardHeader.displayName = 'CardHeader';

export const CardTitle = forwardRef<HTMLParagraphElement, HTMLAttributes<HTMLHeadingElement>>(
  ({ className, ...props }, ref) => (
    <h3
      ref={ref}
      className={cn('text-xl font-semibold leading-none tracking-tight', className)}
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
    <div ref={ref} className={cn('p-6 pt-0', className)} {...props} />
  ),
);
CardContent.displayName = 'CardContent';

export const CardFooter = forwardRef<HTMLDivElement, HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn('flex items-center p-6 pt-0', className)} {...props} />
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
    <Card ref={ref} className={cn('p-6 relative overflow-hidden group hover:border-primary/45', className)} {...props}>
      <div className="flex justify-between items-start mb-4">
        <span className="text-sm font-medium text-muted-foreground">{title}</span>
        {Icon && (
          <div className="w-10 h-10 rounded-lg bg-primary/10 border border-primary/20 flex items-center justify-center text-primary group-hover:scale-110 transition-transform">
            <Icon className="w-5 h-5" />
          </div>
        )}
      </div>
      <div>
        <h3 className="text-3xl font-extrabold text-foreground tracking-tight mb-1">{value}</h3>
        <div className="flex items-center gap-2">
          {trend && (
            <span
              className={cn(
                'inline-flex items-center text-xs font-semibold gap-0.5 px-2 py-0.5 rounded-full border',
                trend.isPositive
                  ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                  : 'bg-destructive/10 text-destructive border-destructive/20'
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
      className={cn(
        'p-6 cursor-pointer border border-border/70 hover:border-primary/45 hover:-translate-y-0.5 group active:translate-y-0',
        className
      )}
      {...props}
    >
      <div className="w-12 h-12 rounded-xl bg-primary/10 border border-primary/20 flex items-center justify-center text-primary mb-4 group-hover:scale-105 transition-transform">
        <Icon className="w-6 h-6" />
      </div>
      <h3 className="text-lg font-bold text-foreground mb-1 group-hover:text-primary transition-colors">{title}</h3>
      <p className="text-sm text-muted-foreground mb-4 line-clamp-2">{description}</p>
      <span className="text-xs font-semibold text-primary inline-flex items-center gap-1 group-hover:translate-x-0.5 transition-transform">
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
        ? 'text-emerald-500'
        : score >= 75
        ? 'text-sky-500'
        : score >= 55
        ? 'text-amber-500'
        : 'text-red-500';

    return (
      <Card ref={ref} className={cn('p-6', className)} {...props}>
        <div className="flex items-center gap-4 mb-6">
          {/* Circular Progress Ring */}
          <div className="relative w-16 h-16 flex-shrink-0">
            <svg className="w-full h-full transform -rotate-90" viewBox="0 0 36 36">
              <path
                className="text-border/40"
                strokeWidth="3.5"
                stroke="currentColor"
                fill="none"
                d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
              />
              <path
                className={cn('transition-all duration-500 ease-out', ringColor)}
                strokeWidth="3.5"
                strokeDasharray={`${score}, 100`}
                strokeLinecap="round"
                stroke="currentColor"
                fill="none"
                d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
              />
            </svg>
            <div className="absolute inset-0 flex items-center justify-center font-bold text-base text-foreground">
              {score}
            </div>
          </div>
          <div>
            <h3 className="font-bold text-foreground">{label}</h3>
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
                        ? 'bg-red-500'
                        : factor.status === 'warning'
                        ? 'bg-amber-500'
                        : 'bg-sky-500'
                    )}
                  />
                  {factor.label}
                </span>
                <span className="font-semibold text-foreground">{factor.impact} pts</span>
              </div>
            ))}
          </div>
        ) : (
          <div className="flex items-center gap-2 p-3 bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 rounded-xl text-xs">
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
      available: { label: 'Disponível', color: 'text-emerald-400 border-emerald-500/20 bg-emerald-500/10' },
      missing: { label: 'Pendente', color: 'text-amber-400 border-amber-500/20 bg-amber-500/10' },
      expired: { label: 'Expirado', color: 'text-red-400 border-red-500/20 bg-red-500/10' },
      review: { label: 'Em revisão', color: 'text-sky-400 border-sky-500/20 bg-sky-500/10' },
    };

    const config = statusConfig[status];

    return (
      <Card
        ref={ref}
        onClick={onClick}
        className={cn(
          'p-4 flex items-center justify-between border border-border/70 hover:border-primary/45 transition-colors cursor-pointer group',
          className
        )}
        {...props}
      >
        <div className="flex items-center gap-3 min-w-0">
          <div className="w-10 h-10 rounded-lg bg-muted flex items-center justify-center text-muted-foreground flex-shrink-0 group-hover:text-primary transition-colors">
            <FileText className="w-5 h-5" />
          </div>
          <div className="min-w-0">
            <h4 className="text-sm font-semibold text-foreground truncate">{name}</h4>
            <p className="text-xs text-muted-foreground truncate">{type}</p>
          </div>
        </div>
        <div className="flex flex-col items-end gap-1.5 flex-shrink-0">
          <span className={cn('px-2.5 py-0.5 rounded-full text-[10px] font-semibold border', config.color)}>
            {config.label}
          </span>
          <span className="text-[10px] text-muted-foreground">{date}</span>
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
      <Card ref={ref} className={cn('p-5 hover:border-primary/40 relative group', className)} {...props}>
        <div className="flex items-start justify-between mb-4">
          <div>
            <span className="text-[10px] uppercase tracking-wider font-extrabold text-primary mb-1 block">
              Certificado {type}
            </span>
            <h4 className="font-bold text-foreground text-base leading-tight">{label}</h4>
          </div>
          {(isCritical || isWarning) && (
            <div className={cn('p-1.5 rounded-md', isCritical ? 'bg-red-500/10 text-red-500' : 'bg-amber-500/10 text-amber-500')}>
              <ShieldAlert className="w-5 h-5" />
            </div>
          )}
        </div>

        <div className="mb-4">
          <div className="flex justify-between items-center text-xs mb-1">
            <span className="text-muted-foreground">Validade: {expiryDate}</span>
            <span className={cn('font-bold', isCritical ? 'text-red-500' : isWarning ? 'text-amber-500' : 'text-emerald-400')}>
              {daysRemaining} dias restantes
            </span>
          </div>
          {/* Progress bar */}
          <div className="h-1.5 bg-muted rounded-full overflow-hidden">
            <div
              className={cn(
                'h-full rounded-full transition-all duration-300',
                isCritical ? 'bg-red-500' : isWarning ? 'bg-amber-500' : 'bg-emerald-500'
              )}
              style={{ width: `${Math.min(100, (daysRemaining / 365) * 100)}%` }}
            />
          </div>
        </div>

        {onWarnClient && (isCritical || isWarning) && (
          <button
            onClick={onWarnClient}
            className="w-full py-2 bg-primary/10 hover:bg-primary/20 text-primary border border-primary/25 rounded-lg text-xs font-semibold hover:-translate-y-px active:translate-y-0 active:scale-[0.98] transition-all"
          >
            Avisar Cliente
          </button>
        )}
      </Card>
    );
  }
);
CertificateCard.displayName = 'CertificateCard';

