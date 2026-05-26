import { AlertCircle } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/Card';
import { type InvoiceRejectionResponse } from '../services/invoices.service';

interface InvoiceRejectionAlertProps {
  rejections: InvoiceRejectionResponse[];
}

export function InvoiceRejectionAlert({ rejections }: InvoiceRejectionAlertProps) {
  if (!rejections || rejections.length === 0) return null;

  return (
    <Card className="border-red-500/20 bg-red-500/5 text-red-600 dark:text-red-400">
      <CardContent className="flex gap-3 p-4">
        <AlertCircle className="h-5 w-5 shrink-0 mt-0.5" />
        <div className="space-y-1">
          <h4 className="text-sm font-semibold text-red-800 dark:text-red-300">
            Erros de Emissão do Órgão Gerador (NFS-e Rejeitada)
          </h4>
          <ul className="list-disc pl-4 text-xs space-y-1">
            {rejections.map((rej) => (
              <li key={rej.id} className="leading-relaxed">
                {rej.codigo_rejeicao && (
                  <span className="font-mono font-bold mr-1">
                    [{rej.codigo_rejeicao}]
                  </span>
                )}
                {rej.descricao}
              </li>
            ))}
          </ul>
        </div>
      </CardContent>
    </Card>
  );
}
