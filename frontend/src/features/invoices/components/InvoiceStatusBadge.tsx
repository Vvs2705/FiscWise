import { Badge, type BadgeVariant } from '@/components/ui/Badge';

interface InvoiceStatusBadgeProps {
  status: string;
}

export function InvoiceStatusBadge({ status }: InvoiceStatusBadgeProps) {
  const getBadgeConfig = (): { variant: BadgeVariant; label: string } => {
    switch (status.toLowerCase()) {
      case 'issued':
        return { variant: 'success', label: 'Emitida' };
      case 'cancelled':
        return { variant: 'error', label: 'Cancelada' };
      case 'rejected':
        return { variant: 'error', label: 'Rejeitada' };
      case 'failed':
        return { variant: 'error', label: 'Falhou' };
      case 'draft':
        return { variant: 'default', label: 'Rascunho' };
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
