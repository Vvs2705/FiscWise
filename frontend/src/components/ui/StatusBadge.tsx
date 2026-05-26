import { ReactNode } from 'react';
import { AlertTriangle, CheckCircle2, Info, XCircle } from 'lucide-react';
import { cn } from '@/lib/utils';

// ─── StatusBadge ───────────────────────────────────────────────────────────

const STATUS_CONFIGS: Record<string, { label: string; color: string }> = {
  // Notas
  draft: { label: 'Rascunho', color: 'bg-muted text-muted-foreground' },
  validating: { label: 'Validando', color: 'bg-blue-500/10 text-blue-400' },
  ready_to_issue: { label: 'Pronta p/ emitir', color: 'bg-emerald-500/10 text-emerald-400' },
  issuing: { label: 'Emitindo', color: 'bg-yellow-500/10 text-yellow-400' },
  processing: { label: 'Processando', color: 'bg-blue-500/10 text-blue-400' },
  issued: { label: 'Emitida', color: 'bg-emerald-500/10 text-emerald-400' },
  rejected: { label: 'Rejeitada', color: 'bg-red-500/10 text-red-400' },
  cancel_requested: { label: 'Cancel. solicitado', color: 'bg-orange-500/10 text-orange-400' },
  cancelled: { label: 'Cancelada', color: 'bg-muted text-muted-foreground' },
  failed: { label: 'Falha', color: 'bg-red-500/10 text-red-400' },
  // Guias
  generated: { label: 'Gerada', color: 'bg-blue-500/10 text-blue-400' },
  sent_to_customer: { label: 'Enviada ao cliente', color: 'bg-purple-500/10 text-purple-400' },
  awaiting_payment: { label: 'Aguard. pagamento', color: 'bg-yellow-500/10 text-yellow-400' },
  paid: { label: 'Paga', color: 'bg-emerald-500/10 text-emerald-400' },
  overdue: { label: 'Vencida', color: 'bg-red-500/10 text-red-400' },
  divergent: { label: 'Divergente', color: 'bg-orange-500/10 text-orange-400' },
  // Procurações
  pending: { label: 'Pendente', color: 'bg-yellow-500/10 text-yellow-400' },
  active: { label: 'Ativa', color: 'bg-emerald-500/10 text-emerald-400' },
  expired: { label: 'Vencida', color: 'bg-red-500/10 text-red-400' },
  revoked: { label: 'Revogada', color: 'bg-muted text-muted-foreground' },
  invalid: { label: 'Inválida', color: 'bg-red-500/10 text-red-400' },
  unknown: { label: 'Desconhecido', color: 'bg-muted text-muted-foreground' },
  // Certificados
  valid: { label: 'Válido', color: 'bg-emerald-500/10 text-emerald-400' },
  expiring: { label: 'Vencendo', color: 'bg-orange-500/10 text-orange-400' },
  // Fechamento
  not_started: { label: 'Não iniciado', color: 'bg-muted text-muted-foreground' },
  in_progress: { label: 'Em andamento', color: 'bg-blue-500/10 text-blue-400' },
  blocked: { label: 'Bloqueado', color: 'bg-red-500/10 text-red-400' },
  ready_for_review: { label: 'Pronto p/ revisão', color: 'bg-purple-500/10 text-purple-400' },
  completed: { label: 'Concluído', color: 'bg-emerald-500/10 text-emerald-400' },
  reopened: { label: 'Reaberto', color: 'bg-orange-500/10 text-orange-400' },
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
  critical: { label: 'Crítico', color: 'bg-red-500/10 text-red-400 border border-red-500/20', icon: <XCircle className="h-3 w-3" /> },
  high: { label: 'Alto', color: 'bg-orange-500/10 text-orange-400 border border-orange-500/20', icon: <AlertTriangle className="h-3 w-3" /> },
  medium: { label: 'Médio', color: 'bg-yellow-500/10 text-yellow-400 border border-yellow-500/20', icon: <Info className="h-3 w-3" /> },
  low: { label: 'Baixo', color: 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20', icon: <CheckCircle2 className="h-3 w-3" /> },
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
