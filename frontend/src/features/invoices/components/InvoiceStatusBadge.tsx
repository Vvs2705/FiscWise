import { Badge, type BadgeVariant } from '@/components/ui/Badge';

interface InvoiceStatusBadgeProps {
  status: string;
  /**
   * `issued_at` vindo do servidor. Quando informado como null/vazio, uma nota
   * com status `issued` NÃO é mostrada como "Emitida" (OFFLINE_SYNC.md, seção 6.1).
   */
  issuedAt?: string | null;
}

export function InvoiceStatusBadge({ status, issuedAt }: InvoiceStatusBadgeProps) {
  const getBadgeConfig = (): { variant: BadgeVariant; label: string } => {
    switch (status.toLowerCase()) {
      case 'issued':
        if (issuedAt === null || issuedAt === '') {
          return { variant: 'warning', label: 'Aguardando confirmação' };
        }
        return { variant: 'success', label: 'Emitida' };
      case 'cancelled':
        return { variant: 'error', label: 'Cancelada' };
      case 'rejected':
        return { variant: 'error', label: 'Rejeitada' };
      case 'failed':
        return { variant: 'error', label: 'Falhou' };
      case 'draft':
        return { variant: 'default', label: 'Rascunho' };
      case 'pending_transmission':
        return { variant: 'warning', label: 'Pendente de transmissão' };
      case 'validating':
        return { variant: 'warning', label: 'Validando' };
      case 'queued':
        return { variant: 'warning', label: 'Na Fila' };
      case 'processing':
        return { variant: 'warning', label: 'Processando' };
      case 'cancel_requested':
        return { variant: 'warning', label: 'Cancelamento Solicitado' };
      case 'replaced':
        return { variant: 'info', label: 'Substituída' };
      default:
        return { variant: 'info', label: status };
    }
  };

  const { variant, label } = getBadgeConfig();
  return <Badge variant={variant}>{label}</Badge>;
}
