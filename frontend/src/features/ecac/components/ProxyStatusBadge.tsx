import { Badge, type BadgeVariant } from '@/components/ui/Badge';

interface ProxyStatusBadgeProps {
  status: string;
}

export function ProxyStatusBadge({ status }: ProxyStatusBadgeProps) {
  const getBadgeConfig = (): { variant: BadgeVariant; label: string } => {
    switch (status.toLowerCase()) {
      case 'ativa':
      case 'active':
        return { variant: 'success', label: 'Ativa' };
      case 'revogada':
      case 'revoked':
        return { variant: 'error', label: 'Revogada' };
      case 'vencida':
      case 'expired':
        return { variant: 'critical', label: 'Vencida' };
      default:
        return { variant: 'info', label: status };
    }
  };

  const { variant, label } = getBadgeConfig();
  return <Badge variant={variant}>{label}</Badge>;
}
