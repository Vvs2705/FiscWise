import { motion } from 'framer-motion';
import { FileText, Upload, CheckCircle2, XCircle } from 'lucide-react';
import { fadeIn } from '../../../lib/motion';

interface PendingDocument {
  id: string;
  clientName: string;
  documentType: string;
  daysWaiting: number;
  status: 'awaiting_client' | 'received' | 'approved' | 'rejected';
}

interface PendingDocumentsCardProps {
  documents: PendingDocument[];
  totalPending: number;
  isLoading?: boolean;
}

const statusConfig = {
  awaiting_client: {
    label: 'Aguardando cliente',
    icon: Upload,
    color: 'text-fw-warning',
    bg: 'bg-fw-warning-soft',
    border: 'border-fw-warning/30',
  },
  received: {
    label: 'Recebido',
    icon: FileText,
    color: 'text-fw-blue',
    bg: 'bg-fw-blue-soft',
    border: 'border-fw-blue/30',
  },
  approved: {
    label: 'Aprovado',
    icon: CheckCircle2,
    color: 'text-fw-success',
    bg: 'bg-fw-success-soft',
    border: 'border-fw-success/30',
  },
  rejected: {
    label: 'Rejeitado',
    icon: XCircle,
    color: 'text-fw-danger',
    bg: 'bg-fw-danger-soft',
    border: 'border-fw-danger/30',
  },
};

export function PendingDocumentsCard({
  documents,
  totalPending,
  isLoading,
}: PendingDocumentsCardProps) {
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

  if (documents.length === 0) {
    return (
      <motion.div
        variants={fadeIn}
        className="bg-fw-surface-solid border border-fw-border rounded-xl p-8 text-center"
      >
        <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-fw-success-soft flex items-center justify-center">
          <CheckCircle2 className="w-8 h-8 text-fw-success" />
        </div>
        <h3 className="text-lg font-semibold text-fw-text mb-2">
          Todos os documentos em dia
        </h3>
        <p className="text-fw-text-muted text-sm">
          Não há documentos pendentes no momento.
        </p>
      </motion.div>
    );
  }

  return (
    <motion.div
      variants={fadeIn}
      className="bg-fw-surface-solid border border-fw-border rounded-xl p-6"
    >
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-fw-text flex items-center gap-2">
          <FileText className="w-5 h-5 text-fw-primary" />
          Documentos Pendentes
        </h2>
        <span className="px-3 py-1 rounded-full text-sm font-semibold bg-fw-warning-soft text-fw-warning border border-fw-warning/30">
          {totalPending} pendentes
        </span>
      </div>

      <div className="space-y-3">
        {documents.map((doc) => {
          const config = statusConfig[doc.status];
          const Icon = config.icon;

          return (
            <div
              key={doc.id}
              className="bg-fw-surface border border-fw-border rounded-lg p-4 hover:border-fw-primary/30 transition-all cursor-pointer group"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-start gap-3 flex-1 min-w-0">
                  <div
                    className={`w-10 h-10 rounded-lg ${config.bg} flex items-center justify-center flex-shrink-0 border ${config.border}`}
                  >
                    <Icon className={`w-5 h-5 ${config.color}`} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <h3 className="font-semibold text-fw-text truncate">
                      {doc.clientName}
                    </h3>
                    <p className="text-sm text-fw-text-muted truncate">
                      {doc.documentType}
                    </p>
                    <p className="text-xs text-fw-text-soft mt-1">
                      {doc.daysWaiting === 0
                        ? 'Hoje'
                        : doc.daysWaiting === 1
                        ? 'Há 1 dia'
                        : `Há ${doc.daysWaiting} dias`}
                    </p>
                  </div>
                </div>
                <span
                  className={`px-2 py-1 rounded-full text-xs font-semibold border flex-shrink-0 ${config.bg} ${config.color} ${config.border}`}
                >
                  {config.label}
                </span>
              </div>
            </div>
          );
        })}
      </div>

      {totalPending > documents.length && (
        <button className="w-full mt-4 py-2 text-sm font-medium text-fw-primary hover:text-fw-primary-strong transition-colors">
          Ver todos os {totalPending} documentos
        </button>
      )}
    </motion.div>
  );
}
