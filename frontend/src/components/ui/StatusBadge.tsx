import { ReactNode } from 'react';
import { AlertTriangle, CheckCircle2, Info, XCircle } from 'lucide-react';
import { cn } from '@/lib/utils';
import { BADGE_TONES as T } from './Badge';

// ─── StatusBadge ───────────────────────────────────────────────────────────

const STATUS_CONFIGS: Record<string, { label: string; color: string }> = {
  // Notas
  draft: { label: 'Rascunho', color: T.neutral },
  validating: { label: 'Validando', color: T.info },
  ready_to_issue: { label: 'Pronta p/ emitir', color: T.success },
  issuing: { label: 'Emitindo', color: T.warning },
  processing: { label: 'Processando', color: T.info },
  issued: { label: 'Emitida', color: T.success },
  rejected: { label: 'Rejeitada', color: T.danger },
  cancel_requested: { label: 'Cancel. solicitado', color: T.warning },
  cancelled: { label: 'Cancelada', color: T.neutral },
  failed: { label: 'Falha', color: T.danger },
  // Guias
  generated: { label: 'Gerada', color: T.info },
  sent_to_customer: { label: 'Enviada ao cliente', color: T.info },
  awaiting_payment: { label: 'Aguard. pagamento', color: T.warning },
  paid: { label: 'Paga', color: T.success },
  overdue: { label: 'Vencida', color: T.danger },
  divergent: { label: 'Divergente', color: T.warning },
  // Procurações
  pending: { label: 'Pendente', color: T.warning },
  active: { label: 'Ativa', color: T.success },
  expired: { label: 'Vencida', color: T.danger },
  revoked: { label: 'Revogada', color: T.neutral },
  invalid: { label: 'Inválida', color: T.danger },
  unknown: { label: 'Desconhecido', color: T.neutral },
  // Certificados
  valid: { label: 'Válido', color: T.success },
  expiring: { label: 'Vencendo', color: T.warning },
  // Fechamento
  not_started: { label: 'Não iniciado', color: T.neutral },
  in_progress: { label: 'Em andamento', color: T.info },
  blocked: { label: 'Bloqueado', color: T.danger },
  ready_for_review: { label: 'Pronto p/ revisão', color: T.info },
  completed: { label: 'Concluído', color: T.success },
  reopened: { label: 'Reaberto', color: T.warning },
};

interface StatusBadgeProps {
  status: string;
  className?: string;
}

export function StatusBadge({ status, className }: StatusBadgeProps) {
  const config = STATUS_CONFIGS[status] ?? { label: status, color: T.neutral };
  return (
    <span className={cn('inline-flex items-center whitespace-nowrap rounded-sm border px-2 py-0.5 text-xs font-medium', config.color, className)}>
      {config.label}
    </span>
  );
}

// ─── RiskBadge ─────────────────────────────────────────────────────────────

const RISK_CONFIGS: Record<string, { label: string; color: string; icon: ReactNode }> = {
  critical: { label: 'Crítico', color: T.danger, icon: <XCircle className="h-3 w-3" aria-hidden="true" /> },
  high: { label: 'Alto', color: T.warning, icon: <AlertTriangle className="h-3 w-3" aria-hidden="true" /> },
  medium: { label: 'Médio', color: T.warning, icon: <Info className="h-3 w-3" aria-hidden="true" /> },
  low: { label: 'Baixo', color: T.success, icon: <CheckCircle2 className="h-3 w-3" aria-hidden="true" /> },
  none: { label: 'Normal', color: T.neutral, icon: null },
};

interface RiskBadgeProps {
  risk: 'critical' | 'high' | 'medium' | 'low' | 'none';
  className?: string;
}

export function RiskBadge({ risk, className }: RiskBadgeProps) {
  const config = RISK_CONFIGS[risk] ?? RISK_CONFIGS.none;
  return (
    <span className={cn('inline-flex items-center gap-1 whitespace-nowrap rounded-sm border px-2 py-0.5 text-xs font-medium', config.color, className)}>
      {config.icon}
      {config.label}
    </span>
  );
}
