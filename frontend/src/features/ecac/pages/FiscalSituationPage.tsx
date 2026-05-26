import { useState } from 'react';
import { FiscalSituationCard } from '../components/FiscalSituationCard';
import { Card, CardContent } from '@/components/ui/Card';
import { Select } from '@/components/ui/Select';
import { useClients } from '@/lib/hooks/useOperations';

export function FiscalSituationPage() {
  const { data: clients } = useClients();
  const [selectedClientId, setSelectedClientId] = useState('');

  // Auto-select first client
  if (!selectedClientId && clients && clients.length > 0) {
    setSelectedClientId(clients[0].id);
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold text-foreground">Situação Fiscal do Contribuinte</h2>
        <p className="text-sm text-muted-foreground">
          Consulte e acompanhe débitos ativos e pendências cadastrais na Receita Federal
        </p>
      </div>

      <Card className="border-border/60 bg-card">
        <CardContent className="p-4 flex flex-col sm:flex-row sm:items-center gap-4">
          <div className="min-w-[250px] flex-1">
            <label className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground mb-1 block">
              Selecione o Cliente para Consulta
            </label>
            <Select
              value={selectedClientId}
              onChange={(e) => setSelectedClientId(e.target.value)}
              className="w-full"
            >
              <option value="">Selecione um cliente...</option>
              {clients?.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name} {c.document ? `(${c.document})` : ''}
                </option>
              ))}
            </Select>
          </div>
        </CardContent>
      </Card>

      {selectedClientId ? (
        <FiscalSituationCard clientId={selectedClientId} />
      ) : (
        <div className="flex flex-col items-center justify-center p-8 border border-dashed border-border/40 rounded-lg text-muted-foreground text-sm">
          Selecione um cliente acima para visualizar a situação fiscal.
        </div>
      )}
    </div>
  );
}
export default FiscalSituationPage;
