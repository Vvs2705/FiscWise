import { usePendingReceipts } from '../hooks/useGuias';
import { Card, CardContent } from '@/components/ui/Card';
import { AlertCircle } from 'lucide-react';
import { Link } from 'react-router-dom';

export function PendingReceiptAlert() {
  const { data: guides, isLoading } = usePendingReceipts();

  if (isLoading || !guides || guides.length === 0) return null;

  return (
    <Card className="border-warning/20 bg-warning/5 text-warning dark:text-warning">
      <CardContent className="flex gap-3 p-4">
        <AlertCircle className="h-5 w-5 shrink-0 mt-0.5" />
        <div className="space-y-1">
          <h4 className="text-sm font-semibold text-warning dark:text-warning">
            Guias pagas pendentes de comprovante ({guides.length})
          </h4>
          <p className="text-xs text-muted-foreground">
            As seguintes guias foram declaradas como pagas mas necessitam de anexo de comprovante:
          </p>
          <ul className="list-disc pl-4 text-xs space-y-1 mt-2">
            {guides.map((guide) => (
              <li key={guide.id} className="leading-relaxed">
                <Link to={`/guias/${guide.id}`} className="font-semibold text-foreground underline hover:text-primary mr-2">
                  {guide.tipo} - {guide.competencia.substring(0, 7)}
                </Link>
                - Valor: {guide.valor.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}
              </li>
            ))}
          </ul>
        </div>
      </CardContent>
    </Card>
  );
}
export default PendingReceiptAlert;
