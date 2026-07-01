import { motion } from 'framer-motion';
import { AlertCircle, Clock, FileWarning, Shield } from 'lucide-react';
import { staggerContainer, fadeIn } from '../../../lib/motion';

interface ClientAttentionItem {
  id: string;
  name: string;
  reason: string;
  risk: 'Alto' | 'Médio' | 'Baixo' | 'Regular';
  icon: 'alert' | 'clock' | 'document' | 'certificate';
}

interface ClientAttentionListProps {
  clients: ClientAttentionItem[];
  isLoading?: boolean;
}

const riskStyles = {
  Alto: 'bg-destructive/10 text-destructive border-destructive/30',
  Médio: 'bg-warning/10 text-warning border-warning/30',
  Baixo: 'bg-info/10 text-info border-info/30',
  Regular: 'bg-success/10 text-success border-success/30',
};

const iconMap = {
  alert: AlertCircle,
  clock: Clock,
  document: FileWarning,
  certificate: Shield,
};

export function ClientAttentionList({ clients, isLoading }: ClientAttentionListProps) {
  if (isLoading) {
    return (
      <div className="bg-card border border-border rounded-card shadow-token-sm p-6">
        <div className="h-6 w-48 bg-muted animate-pulse rounded mb-4" />
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-16 bg-muted animate-pulse rounded-lg" />
          ))}
        </div>
      </div>
    );
  }

  if (clients.length === 0) {
    return (
      <motion.div
        variants={fadeIn}
        className="bg-card border border-border rounded-card shadow-token-sm p-8 text-center"
      >
        <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-success/10 flex items-center justify-center">
          <Shield className="w-8 h-8 text-success" />
        </div>
        <h3 className="text-lg font-semibold text-foreground mb-2">
          Todos os clientes estão em dia
        </h3>
        <p className="text-muted-foreground text-sm">
          Nenhum cliente precisa de atenção imediata no momento.
        </p>
      </motion.div>
    );
  }

  return (
    <motion.div
      variants={staggerContainer}
      initial="initial"
      animate="animate"
      className="bg-card border border-border rounded-card shadow-token-sm p-6"
    >
      <h2 className="text-lg font-semibold text-foreground mb-4">
        Clientes que precisam de atenção
      </h2>

      <div className="space-y-3">
        {clients.map((client) => {
          const Icon = iconMap[client.icon];
          return (
            <motion.div
              key={client.id}
              variants={fadeIn}
              className="bg-muted border border-border rounded-lg p-4 hover:border-primary/30 transition-all cursor-pointer group"
            >
              <div className="flex items-center justify-between gap-4">
                <div className="flex items-center gap-3 flex-1 min-w-0">
                  <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center flex-shrink-0 group-hover:bg-primary/20 transition-colors">
                    <Icon className="w-5 h-5 text-primary" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <h3 className="font-semibold text-foreground truncate">
                      {client.name}
                    </h3>
                    <p className="text-sm text-muted-foreground truncate">
                      {client.reason}
                    </p>
                  </div>
                </div>
                <span
                  className={`px-3 py-1 rounded-full text-xs font-semibold border flex-shrink-0 ${
                    riskStyles[client.risk]
                  }`}
                >
                  {client.risk}
                </span>
              </div>
            </motion.div>
          );
        })}
      </div>
    </motion.div>
  );
}
