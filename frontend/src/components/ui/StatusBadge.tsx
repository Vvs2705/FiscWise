import { ReactNode } from 'react';
import { AlertTriangle, CheckCircle2, Info, XCircle } from 'lucide-react';
import { cn } from '@/lib/utils';

// ─── StatusBadge ───────────────────────────────────────────────────────────

const STATUS_CONFIGS: Record<string, { label: string; color: string }> = {
  // Notas
  draft: { label: 'Rascunho', color: 'bg-muted text-muted-foreground' },
  validating: { label: 'Validando', color: 'bg-info/10 text-info' },
  ready_to_issue: { label: 'Pronta p/ emitir', color: 'bg-success/10 text-success' },
  issuing: { label: 'Emitindo', color: 'bg-warning/10 text-warning' },
  processing: { label: 'Processando', color: 'bg-info/10 text-info' },
  issued: { label: 'Emitida', color: 'bg-success/10 text-success' },
  rejected: { label: 'Rejeitada', color: 'bg-destructive/10 text-destructive' },
  cancel_requested: { label: 'Cancel. solicitado', color: 'bg-warning/10 text-warning' },
  cancelled: { label: 'Cancelada', color: 'bg-muted text-muted-foreground' },
  failed: { label: 'Falha', color: 'bg-destructive/10 text-destructive' },
  // Guias
  generated: { label: 'Gerada', color: 'bg-info/10 text-info' },
  sent_to_customer: { label: 'Enviada ao cliente', color: 'bg-info/10 text-info' },
  awaiting_payment: { label: 'Aguard. pagamento', color: 'bg-warning/10 text-warning' },
  paid: { label: 'Paga', color: 'bg-success/10 text-success' },
  overdue: { label: 'Vencida', color: 'bg-destructive/10 text-destructive' },
  divergent: { label: 'Divergente', color: 'bg-warning/10 text-warning' },
  // Procurações
  pending: { label: 'Pendente', color: 'bg-warning/10 text-warning' },
  active: { label: 'Ativa', color: 'bg-success/10 text-success' },
  expired: { label: 'Vencida', color: 'bg-destructive/10 text-destructive' },
  revoked: { label: 'Revogada', color: 'bg-muted text-muted-foreground' },
  invalid: { label: 'Inválida', color: 'bg-destructive/10 text-destructive' },
  unknown: { label: 'Desconhecido', color: 'bg-muted text-muted-foreground' },
  // Certificados
  valid: { label: 'Válido', color: 'bg-success/10 text-success' },
  expiring: { label: 'Vencendo', color: 'bg-warning/10 text-warning' },
  // Fechamento
  not_started: { label: 'Não iniciado', color: 'bg-muted text-muted-foreground' },
  in_progress: { label: 'Em andamento', color: 'bg-info/10 text-info' },
  blocked: { label: 'Bloqueado', color: 'bg-destructive/10 text-destructive' },
  ready_for_review: { label: 'Pronto p/ revisão', color: 'bg-info/10 text-info' },
  completed: { label: 'Concluído', color: 'bg-success/10 text-success' },
  reopened: { label: 'Reaberto', color: 'bg-warning/10 text-warning' },
};

interface StatusBadgeProps {
  status: string;
  className?: string;
}

export function StatusBadge({ status, className }: StatusBadgeProps) {
  const config = STATUS_CONFIGS[status] ?? { label: status, color: 'bg-muted text-muted-foreground' };
  return (
    <span className={cn('inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium', config.color, className)}>
      {config.label}
    </span>
  );
}

// ─── RiskBadge ─────────────────────────────────────────────────────────────

const RISK_CONFIGS: Record<string, { label: string; color: string; icon: ReactNode }> = {
  critical: { label: 'Crítico', color: 'bg-destructive/10 text-destructive border border-destructive/20', icon: <XCircle className="h-3 w-3" /> },
  high: { label: 'Alto', color: 'bg-warning/10 text-warning border border-warning/20', icon: <AlertTriangle className="h-3 w-3" /> },
  medium: { label: 'Médio', color: 'bg-warning/10 text-warning border border-warning/20', icon: <Info className="h-3 w-3" /> },
  low: { label: 'Baixo', color: 'bg-success/10 text-success border border-success/20', icon: <CheckCircle2 className="h-3 w-3" /> },
  none: { label: 'Normal', color: 'bg-muted text-muted-foreground', icon: null },
};

interface RiskBadgeProps {
  risk: 'critical' | 'high' | 'medium' | 'low' | 'none';
  className?: string;
}

export function RiskBadge({ risk, className }: RiskBadgeProps) {
  const config = RISK_CONFIGS[risk] ?? RISK_CONFIGS.none;
  return (
    <span className={cn('inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium', config.color, className)}>
      {config.icon}
      {config.label}
    </span>
  );
}
