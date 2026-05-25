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
  Alto: 'bg-fw-danger-soft text-fw-danger border-fw-danger/30',
  Médio: 'bg-fw-warning-soft text-fw-warning border-fw-warning/30',
  Baixo: 'bg-fw-blue-soft text-fw-blue border-fw-blue/30',
  Regular: 'bg-fw-success-soft text-fw-success border-fw-success/30',
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
      <div className="bg-fw-surface-solid border border-fw-border rounded-xl p-6">
        <div className="h-6 w-48 bg-fw-surface animate-pulse rounded mb-4" />
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-16 bg-fw-surface animate-pulse rounded-lg" />
          ))}
        </div>
      </div>
    );
  }

  if (clients.length === 0) {
    return (
      <motion.div
        variants={fadeIn}
        className="bg-fw-surface-solid border border-fw-border rounded-xl p-8 text-center"
      >
        <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-fw-success-soft flex items-center justify-center">
          <Shield className="w-8 h-8 text-fw-success" />
        </div>
        <h3 className="text-lg font-semibold text-fw-text mb-2">
          Todos os clientes estão em dia
        </h3>
        <p className="text-fw-text-muted text-sm">
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
      className="bg-fw-surface-solid border border-fw-border rounded-xl p-6"
    >
      <h2 className="text-lg font-semibold text-fw-text mb-4">
        Clientes que precisam de atenção
      </h2>

      <div className="space-y-3">
        {clients.map((client) => {
          const Icon = iconMap[client.icon];
          return (
            <motion.div
              key={client.id}
              variants={fadeIn}
              className="bg-fw-surface border border-fw-border rounded-lg p-4 hover:border-fw-primary/30 transition-all cursor-pointer group"
            >
              <div className="flex items-center justify-between gap-4">
                <div className="flex items-center gap-3 flex-1 min-w-0">
                  <div className="w-10 h-10 rounded-lg bg-fw-primary-soft flex items-center justify-center flex-shrink-0 group-hover:bg-fw-primary/20 transition-colors">
                    <Icon className="w-5 h-5 text-fw-primary" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <h3 className="font-semibold text-fw-text truncate">
                      {client.name}
                    </h3>
                    <p className="text-sm text-fw-text-muted truncate">
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
