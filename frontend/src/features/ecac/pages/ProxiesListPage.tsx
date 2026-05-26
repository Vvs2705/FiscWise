import { useState } from 'react';
import { useProxies, useCreateProxy, useExpiringProxies, useUpdateProxy } from '../hooks/useEcac';
import { ProxyStatusBadge } from '../components/ProxyStatusBadge';
import { ProxyExpirationAlert } from '../components/ProxyExpirationAlert';
import { ClientsWithoutProxyList } from '../components/ClientsWithoutProxyList';
import { Card, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Dialog } from '@/components/ui/Dialog';
import { FormField } from '@/components/ui/FormField';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import { PageSpinner } from '@/components/ui/StateViews';
import { Plus } from 'lucide-react';
import { useClients } from '@/lib/hooks/useOperations';
import { useForm } from 'react-hook-form';
import toast from 'react-hot-toast';

type FormValues = {
  client_id: string;
  outorgante_cpf_cnpj: string;
  outorgante_nome: string;
  procurador_cpf: string;
  tipo: string;
  data_inicio: string;
  data_validade: string;
};

export function ProxiesListPage() {
  const [openModal, setOpenModal] = useState(false);
  const { data: clients } = useClients();
  const { data: proxies, isLoading: proxiesLoading } = useProxies();
  const { data: expiring } = useExpiringProxies();
  const createProxy = useCreateProxy();
  const updateProxy = useUpdateProxy();

  const {
    register,
    handleSubmit,
    reset,
    formState: { isSubmitting },
  } = useForm<FormValues>({
    defaultValues: {
      client_id: '',
      outorgante_cpf_cnpj: '',
      outorgante_nome: '',
      procurador_cpf: '',
      tipo: 'e-CAC',
      data_inicio: new Date().toISOString().split('T')[0],
      data_validade: '',
    },
  });

  const handleAddProxyForClient = (clientId: string) => {
    const client = clients?.find((c) => c.id === clientId);
    if (client) {
      reset({
        client_id: client.id,
        outorgante_cpf_cnpj: client.document || '',
        outorgante_nome: client.name,
        procurador_cpf: '',
        tipo: 'e-CAC',
        data_inicio: new Date().toISOString().split('T')[0],
        data_validade: '',
      });
      setOpenModal(true);
    }
  };

  const onSubmit = async (data: FormValues) => {
    try {
      await createProxy.mutateAsync({
        client_id: data.client_id || undefined,
        outorgante_cpf_cnpj: data.outorgante_cpf_cnpj.replace(/\D/g, ''),
        outorgante_nome: data.outorgante_nome,
        procurador_cpf: data.procurador_cpf.replace(/\D/g, ''),
        tipo: data.tipo,
        servicos_autorizados: ['sit-fiscal', 'nfs-e', 'esocial'],
        data_inicio: data.data_inicio,
        data_validade: data.data_validade || undefined,
        status: 'ativa',
      });
      toast.success('Procuração cadastrada com sucesso!');
      setOpenModal(false);
    } catch (err) {
      console.error(err);
      toast.error('Erro ao cadastrar procuração.');
    }
  };

  const handleRevoke = async (id: string) => {
    if (!window.confirm('Deseja realmente marcar esta procuração como revogada?')) return;
    try {
      await updateProxy.mutateAsync({ id, data: { status: 'revogada' } });
      toast.success('Procuração marcada como revogada.');
    } catch {
      toast.error('Erro ao atualizar status da procuração.');
    }
  };

  if (proxiesLoading) {
    return <PageSpinner />;
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col justify-between gap-4 md:flex-row md:items-center">
        <div>
          <h2 className="text-xl font-bold text-foreground">Procurações e-CAC</h2>
          <p className="text-sm text-muted-foreground">
            Gerencie outorgas e procurações fiscais da Receita Federal
          </p>
        </div>
        <Button onClick={() => setOpenModal(true)} className="flex items-center gap-2">
          <Plus className="h-4 w-4" />
          Nova Procuração
        </Button>
      </div>

      {expiring && expiring.length > 0 && (
        <ProxyExpirationAlert proxies={expiring} />
      )}

      <div className="grid gap-6 md:grid-cols-3">
        {/* Main List column */}
        <div className="space-y-6 md:col-span-2">
          <Card className="border-border/60 bg-card overflow-hidden">
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead>
                    <tr className="border-b border-border/80 bg-muted/30 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                      <th className="px-5 py-3">Outorgante</th>
                      <th className="px-5 py-3">Tipo</th>
                      <th className="px-5 py-3">Status</th>
                      <th className="px-5 py-3">Validade</th>
                      <th className="px-5 py-3 text-right">Ações</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border/40">
                    {proxies?.map((p) => (
                      <tr key={p.id} className="hover:bg-muted/10 transition-colors duration-150">
                        <td className="px-5 py-4">
                          <p className="font-semibold text-foreground">{p.outorgante_nome || 'Cliente'}</p>
                          <p className="text-xs text-muted-foreground">{p.outorgante_cpf_cnpj}</p>
                        </td>
                        <td className="px-5 py-4 text-muted-foreground font-mono text-xs">{p.tipo || 'e-CAC'}</td>
                        <td className="px-5 py-4">
                          <ProxyStatusBadge status={p.status || 'ativa'} />
                        </td>
                        <td className="px-5 py-4 text-muted-foreground">
                          {p.data_validade ? new Date(p.data_validade + 'T00:00:00').toLocaleDateString('pt-BR') : 'Sem prazo'}
                        </td>
                        <td className="px-5 py-4 text-right">
                          {p.status !== 'revogada' && (
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleRevoke(p.id)}
                              className="text-red-500 hover:bg-red-500/10 hover:text-red-600"
                            >
                              Revogar
                            </Button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Warning checklist sidebar */}
        <div>
          <ClientsWithoutProxyList onAddProxyClick={handleAddProxyForClient} />
        </div>
      </div>

      <Dialog
        open={openModal}
        onClose={() => setOpenModal(false)}
        title="Cadastrar Procuração e-CAC"
      >
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <FormField label="Cliente Relacionado (Opcional)" htmlFor="client_id">
            <Select id="client_id" {...register('client_id')}>
              <option value="">Selecione um cliente</option>
              {clients?.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </Select>
          </FormField>

          <FormField label="Razão Social / Nome Outorgante" htmlFor="outorgante_nome">
            <Input type="text" id="outorgante_nome" placeholder="Nome completo ou Razão Social" {...register('outorgante_nome')} required />
          </FormField>

          <div className="grid grid-cols-2 gap-4">
            <FormField label="CNPJ/CPF Outorgante" htmlFor="outorgante_cpf_cnpj">
              <Input type="text" id="outorgante_cpf_cnpj" placeholder="Apenas números" {...register('outorgante_cpf_cnpj')} required />
            </FormField>

            <FormField label="CPF do Procurador (Contador)" htmlFor="procurador_cpf">
              <Input type="text" id="procurador_cpf" placeholder="Apenas números" {...register('procurador_cpf')} required />
            </FormField>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <FormField label="Data de Início" htmlFor="data_inicio">
              <Input type="date" id="data_inicio" {...register('data_inicio')} />
            </FormField>

            <FormField label="Data de Validade (Expiração)" htmlFor="data_validade">
              <Input type="date" id="data_validade" {...register('data_validade')} required />
            </FormField>
          </div>

          <FormField label="Tipo de Outorga" htmlFor="tipo">
            <Select id="tipo" {...register('tipo')}>
              <option value="e-CAC">Portal e-CAC (Receita Federal)</option>
              <option value="NFS-e">Portal Nacional NFS-e</option>
              <option value="eSocial">eSocial</option>
            </Select>
          </FormField>

          <div className="flex justify-end gap-3 pt-2">
            <Button type="button" variant="outline" onClick={() => setOpenModal(false)}>
              Cancelar
            </Button>
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? 'Salvando...' : 'Salvar Procuração'}
            </Button>
          </div>
        </form>
      </Dialog>
    </div>
  );
}
export default ProxiesListPage;
