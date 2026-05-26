import { FiscalTimeline, type TimelineItem } from '@/components/ui/FiscalTimeline';
import { type InvoiceEventResponse } from '../services/invoices.service';
import { 
  PlusCircle, 
  Send, 
  CheckCircle, 
  XCircle, 
  Trash2,
  AlertTriangle 
} from 'lucide-react';

interface InvoiceTimelineProps {
  events: InvoiceEventResponse[];
  isLoading?: boolean;
}

export function InvoiceTimeline({ events, isLoading }: InvoiceTimelineProps) {
  const getEventConfig = (type: string) => {
    switch (type.toLowerCase()) {
      case 'invoice.created':
        return {
          title: 'Rascunho Criado',
          type: 'info' as const,
          icon: PlusCircle,
        };
      case 'invoice.emission_queued':
        return {
          title: 'Envio na Fila',
          type: 'warning' as const,
          icon: Send,
        };
      case 'invoice.issued':
        return {
          title: 'NFS-e Emitida',
          type: 'success' as const,
          icon: CheckCircle,
        };
      case 'invoice.rejected':
        return {
          title: 'Rejeitada pelo Provedor',
          type: 'error' as const,
          icon: AlertTriangle,
        };
      case 'invoice.cancelled':
        return {
          title: 'NFS-e Cancelada',
          type: 'error' as const,
          icon: XCircle,
        };
      case 'invoice.failed':
        return {
          title: 'Falha no Processamento',
          type: 'error' as const,
          icon: Trash2,
        };
      default:
        return {
          title: type,
          type: 'default' as const,
          icon: Send,
        };
    }
  };

  const timelineItems: TimelineItem[] = events.map((event) => {
    const config = getEventConfig(event.event_type);
    
    // Format timestamp nicely
    const dateStr = new Date(event.created_at).toLocaleString('pt-BR');
    
    // Extrapolate payload data if available
    let description = '';
    if (event.payload) {
      if (typeof event.payload === 'string') {
        description = event.payload;
      } else {
        const payloadObj = event.payload as Record<string, unknown>;
        if (typeof payloadObj.reason === 'string') {
          description = `Motivo: ${payloadObj.reason}`;
        } else if (typeof payloadObj.error === 'string') {
          description = `Erro: ${payloadObj.error}`;
        } else if (typeof payloadObj.message === 'string') {
          description = payloadObj.message;
        }
      }
    }

    return {
      id: event.id,
      title: config.title,
      description: description,
      date: dateStr,
      type: config.type,
      icon: config.icon,
    };
  });

  return (
    <div className="space-y-4">
      <h3 className="text-sm font-semibold tracking-tight text-foreground uppercase">
        Histórico de Processamento
      </h3>
      <FiscalTimeline items={timelineItems} isLoading={isLoading} />
    </div>
  );
}
