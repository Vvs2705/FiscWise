import { AlertCircle } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/Card';
import { type EcacProxyResponse } from '../services/ecac.service';

interface ProxyExpirationAlertProps {
  proxies: EcacProxyResponse[];
}

export function ProxyExpirationAlert({ proxies }: ProxyExpirationAlertProps) {
  if (!proxies || proxies.length === 0) return null;

  return (
    <Card className="border-amber-500/20 bg-amber-500/5 text-amber-700 dark:text-amber-400">
      <CardContent className="flex gap-3 p-4">
        <AlertCircle className="h-5 w-5 shrink-0 mt-0.5" />
        <div className="space-y-1">
          <h4 className="text-sm font-semibold text-amber-800 dark:text-amber-300">
            Procurações e-CAC expirando nos próximos 30 dias ({proxies.length})
          </h4>
          <p className="text-xs text-muted-foreground">
            As seguintes procurações fiscais estão próximas do vencimento e precisam de renovação:
          </p>
          <ul className="list-disc pl-4 text-xs space-y-1 mt-2">
            {proxies.map((proxy) => (
              <li key={proxy.id} className="leading-relaxed">
                <span className="font-semibold text-foreground">
                  {proxy.outorgante_nome || 'Cliente sem nome'}
                </span>{' '}
                - CNPJ/CPF: {proxy.outorgante_cpf_cnpj} (Vence em:{' '}
                {proxy.data_validade
                  ? new Date(proxy.data_validade + 'T00:00:00').toLocaleDateString('pt-BR')
                  : '—'}
                )
              </li>
            ))}
          </ul>
        </div>
      </CardContent>
    </Card>
  );
}
