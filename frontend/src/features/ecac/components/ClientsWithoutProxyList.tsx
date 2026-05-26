import { useClientsWithoutProxy } from '../hooks/useEcac';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { ShieldAlert, Plus } from 'lucide-react';

interface ClientsWithoutProxyListProps {
  onAddProxyClick: (clientId: string) => void;
}

export function ClientsWithoutProxyList({ onAddProxyClick }: ClientsWithoutProxyListProps) {
  const { data: clients, isLoading } = useClientsWithoutProxy();

  if (isLoading) {
    return (
      <Card className="border-border/60 bg-card">
        <CardContent className="flex items-center justify-center p-8">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent" />
        </CardContent>
      </Card>
    );
  }

  if (!clients || clients.length === 0) {
    return null;
  }

  return (
    <Card className="border-border/60 bg-card">
      <CardHeader>
        <CardTitle className="text-sm font-semibold tracking-wider uppercase text-muted-foreground flex items-center gap-2">
          <ShieldAlert className="h-4 w-4 text-amber-500" />
          Clientes Sem Procuração e-CAC ({clients.length})
        </CardTitle>
      </CardHeader>
      <CardContent className="p-0">
        <div className="divide-y divide-border/40 max-h-[300px] overflow-y-auto">
          {clients.map((client) => (
            <div key={client.id} className="flex items-center justify-between p-4 hover:bg-muted/5 transition-colors">
              <div>
                <p className="text-sm font-medium text-foreground">{client.name}</p>
                <p className="text-xs text-muted-foreground">{client.document || 'Sem CNPJ/CPF'}</p>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={() => onAddProxyClick(client.id)}
                className="flex items-center gap-1.5 h-8"
              >
                <Plus className="h-3.5 w-3.5" />
                Vincular
              </Button>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
