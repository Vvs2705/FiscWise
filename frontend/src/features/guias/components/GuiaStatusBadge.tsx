import { Badge, type BadgeVariant } from '@/components/ui/Badge';

interface GuiaStatusBadgeProps {
  status: string;
}

export function GuiaStatusBadge({ status }: GuiaStatusBadgeProps) {
  const getBadgeConfig = (): { variant: BadgeVariant; label: string } => {
    switch (status.toLowerCase()) {
      case 'paga':
      case 'paid':
        return { variant: 'success', label: 'Paga' };
      case 'atrasada':
      case 'overdue':
        return { variant: 'error', label: 'Atrasada' };
      case 'enviada':
        return { variant: 'info', label: 'Enviada' };
      case 'pendente':
      default:
        return { variant: 'warning', label: 'Pendente' };
    }
  };

  const { variant, label } = getBadgeConfig();
  return <Badge variant={variant}>{label}</Badge>;
}
