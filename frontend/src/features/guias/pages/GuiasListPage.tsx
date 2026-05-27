import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useGuides, useCreateGuide } from '../hooks/useGuias';
import { GuiaStatusBadge } from '../components/GuiaStatusBadge';
import { PendingReceiptAlert } from '../components/PendingReceiptAlert';
import { Card, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Dialog } from '@/components/ui/Dialog';
import { FormField } from '@/components/ui/FormField';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import { PageSpinner, EmptyState } from '@/components/ui/StateViews';
import { Plus, Eye } from 'lucide-react';
import { useClients } from '@/lib/hooks/useOperations';
import { useForm } from 'react-hook-form';
import { toast } from 'sonner';
import { getApiErrorMessage } from '@/lib/api';
import { formatCurrencyBRL, parseCurrencyBRL } from '@/lib/utils';

type FormValues = {
  client_id: string;
  tipo: 'DAS' | 'DARF' | 'GPS' | 'ISS' | 'outro';
  competencia: string;
  valor: string;
  vencimento: string;
};

export function GuiasListPage() {
  const navigate = useNavigate();
  const [openModal, setOpenModal] = useState(false);
  const [selectedClient, setSelectedClient] = useState('');
  const [selectedStatus, setSelectedStatus] = useState('');
  
  const { data: clients } = useClients();
  const { data: guides, isLoading: guidesLoading } = useGuides({
    client_id: selectedClient || undefined,
    status: selectedStatus || undefined,
  });

  const createGuide = useCreateGuide();

  const {
    register,
    handleSubmit,
    reset,
    formState: { isSubmitting },
  } = useForm<FormValues>({
    defaultValues: {
      client_id: '',
      tipo: 'DAS',
      competencia: new Date().toISOString().split('T')[0],
      valor: '',
      vencimento: new Date().toISOString().split('T')[0],
    },
  });

  const onSubmit = async (data: FormValues) => {
    try {
      const parsedVal = parseCurrencyBRL(data.valor);
      if (!parsedVal || parsedVal <= 0) {
        toast.error('Informe um valor válido para a guia.');
        return;
      }
      await createGuide.mutateAsync({
        client_id: data.client_id,
        tipo: data.tipo,
        competencia: data.competencia,
        valor: parsedVal,
        vencimento: data.vencimento,
      });
      toast.success('Guia cadastrada com sucesso!');
      setOpenModal(false);
      reset();
    } catch (err) {
      toast.error(getApiErrorMessage(err, 'Erro ao cadastrar guia de imposto.'));
    }
  };

  if (guidesLoading) {
    return <PageSpinner />;
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col justify-between gap-4 md:flex-row md:items-center">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground">
            Guias de Impostos e Tributos
          </h1>
          <p className="text-sm text-muted-foreground">
            Acompanhe e anexe comprovantes de DAS, DARF, GPS e tributos municipais
          </p>
        </div>
        <Button onClick={() => setOpenModal(true)} className="flex items-center gap-2">
          <Plus className="h-4 w-4" />
          Registrar Guia
        </Button>
      </div>

      <PendingReceiptAlert />

      {/* Filters Card */}
      <Card className="border-border/60 bg-card">
        <CardContent className="p-4 flex flex-wrap gap-4">
          <div className="min-w-[200px] flex-1">
            <label className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground mb-1 block">
              Filtrar por Cliente
            </label>
            <Select
              value={selectedClient}
              onChange={(e) => setSelectedClient(e.target.value)}
              className="w-full"
            >
              <option value="">Todos os clientes</option>
              {clients?.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </Select>
          </div>

          <div className="min-w-[150px]">
            <label className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground mb-1 block">
              Filtrar por Status
            </label>
            <Select
              value={selectedStatus}
              onChange={(e) => setSelectedStatus(e.target.value)}
              className="w-full"
            >
              <option value="">Todos os status</option>
              <option value="pendente">Pendente</option>
              <option value="enviada">Enviada</option>
              <option value="paga">Paga</option>
              <option value="atrasada">Atrasada</option>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Guides Table */}
      {!guides || guides.length === 0 ? (
        <EmptyState
          title="Nenhuma guia cadastrada"
          description="Registre guias de imposto manualmente ou anexe comprovantes de pagamento."
        />
      ) : (
        <Card className="border-border/60 bg-card overflow-hidden">
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-border/80 bg-muted/30 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                    <th className="px-5 py-3">Tipo da Guia</th>
                    <th className="px-5 py-3">Cliente</th>
                    <th className="px-5 py-3 text-right">Valor (R$)</th>
                    <th className="px-5 py-3">Competência</th>
                    <th className="px-5 py-3">Vencimento</th>
                    <th className="px-5 py-3">Status</th>
                    <th className="px-5 py-3 text-right">Ações</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/40">
                  {guides.map((g) => (
                    <tr key={g.id} className="hover:bg-muted/10 transition-colors duration-150">
                      <td className="px-5 py-4 font-semibold text-foreground">{g.tipo}</td>
                      <td className="px-5 py-4 text-foreground font-medium">
                        {clients?.find((c) => c.id === g.client_id)?.name || 'Cliente'}
                      </td>
                      <td className="px-5 py-4 text-right font-bold text-foreground">
                        {g.valor.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}
                      </td>
                      <td className="px-5 py-4 text-muted-foreground">
                        {new Date(g.competencia + 'T00:00:00').toLocaleDateString('pt-BR', { month: '2-digit', year: 'numeric' })}
                      </td>
                      <td className="px-5 py-4 text-muted-foreground">
                        {new Date(g.vencimento + 'T00:00:00').toLocaleDateString('pt-BR')}
                      </td>
                      <td className="px-5 py-4">
                        <GuiaStatusBadge status={g.status || 'pendente'} />
                      </td>
                      <td className="px-5 py-4 text-right">
                        <Button variant="ghost" size="sm" onClick={() => navigate(`/guias/${g.id}`)}>
                          <Eye className="h-4 w-4" />
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Register Guide Modal */}
      <Dialog
        open={openModal}
        onClose={() => setOpenModal(false)}
        title="Registrar Guia de Imposto"
      >
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <FormField label="Cliente Relacionado" htmlFor="client_id">
            <Select id="client_id" {...register('client_id')} required>
              <option value="">Selecione o cliente...</option>
              {clients?.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </Select>
          </FormField>

          <FormField label="Tipo do Imposto" htmlFor="tipo">
            <Select id="tipo" {...register('tipo')}>
              <option value="DAS">DAS (Simples Nacional)</option>
              <option value="DARF">DARF (IRPJ/CSLL/PIS/COFINS)</option>
              <option value="GPS">GPS (Inss Previdência)</option>
              <option value="ISS">ISS Municipal</option>
              <option value="outro">Outro tributo</option>
            </Select>
          </FormField>

          <div className="grid grid-cols-2 gap-4">
            <FormField label="Competência (Mês)" htmlFor="competencia">
              <Input type="date" id="competencia" {...register('competencia')} />
            </FormField>

            <FormField label="Data de Vencimento" htmlFor="vencimento">
              <Input type="date" id="vencimento" {...register('vencimento')} />
            </FormField>
          </div>

          <FormField label="Valor da Guia (R$)" htmlFor="valor">
            <Input
              type="text"
              id="valor"
              placeholder="0,00"
              {...register('valor', {
                onChange: (e) => {
                  e.target.value = formatCurrencyBRL(e.target.value);
                },
              })}
              required
            />
          </FormField>

          <div className="flex justify-end gap-3 pt-2">
            <Button type="button" variant="outline" onClick={() => setOpenModal(false)}>
              Cancelar
            </Button>
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? 'Gerando...' : 'Salvar Guia'}
            </Button>
          </div>
        </form>
      </Dialog>
    </div>
  );
}
export default GuiasListPage;
