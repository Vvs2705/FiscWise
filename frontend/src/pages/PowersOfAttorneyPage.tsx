import { useState } from 'react';
import {
  FileText, Plus, Search, AlertTriangle, CheckCircle2,
  Clock, ChevronRight, RefreshCw,
} from 'lucide-react';
import { PageHeader } from '@/components/ui/PageHeader';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { MetricCard, EmptyState, WarningPanel } from '@/components/ui/OperationalStates';
import { Button } from '@/components/ui/Button';
import { Dialog } from '@/components/ui/Dialog';
import { FormField } from '@/components/ui/FormField';
import { Input } from '@/components/ui/Input';
import { PageSpinner } from '@/components/ui/StateViews';
import { FeatureGate } from '@/components/ui/FeatureGate';
import { cn } from '@/lib/utils';
import { toast } from 'sonner';
import { getApiErrorMessage } from '@/lib/api';
import { useForm } from 'react-hook-form';
import { useClients } from '@/lib/hooks/useOperations';
import {
  usePowersOfAttorney,
  useCreatePowerOfAttorney,
  useRevokePowerOfAttorney,
} from '@/features/powers-of-attorney/api';

const STATUS_OPTIONS = [
  { value: 'all', label: 'Todos os status' },
  { value: 'active', label: 'Ativas' },
  { value: 'pending', label: 'Pendentes' },
  { value: 'expired', label: 'Vencidas' },
  { value: 'revoked', label: 'Revogadas' },
];

function daysUntil(dateStr: string | null): number {
  if (!dateStr) return 9999;
  const diff = new Date(dateStr).getTime() - new Date().getTime();
  return Math.ceil(diff / (1000 * 60 * 60 * 24));
}

type NewPoaForm = {
  client_id: string;
  cnpj_grantor: string;
  cnpj_attorney: string;
  valid_until: string;
  provider: string;
  notes: string;
};

export function PowersOfAttorneyPage() {
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [openModal, setOpenModal] = useState(false);

  const { data: powers, isLoading, error } = usePowersOfAttorney();
  const { data: clients } = useClients();
  const createPoa = useCreatePowerOfAttorney();
  const revokePoa = useRevokePowerOfAttorney();

  const { register, handleSubmit, reset, formState: { isSubmitting } } = useForm<NewPoaForm>({
    defaultValues: { client_id: '', cnpj_grantor: '', cnpj_attorney: '', valid_until: '', provider: 'e-CAC Receita Federal', notes: '' },
  });

  const list = powers ?? [];

  const filtered = list.filter(p => {
    if (statusFilter !== 'all' && p.status !== statusFilter) return false;
    const client = clients?.find(c => c.id === p.client_id);
    const name = client?.name ?? '';
    if (search && !name.toLowerCase().includes(search.toLowerCase()) &&
        !p.cnpj_grantor.includes(search)) return false;
    return true;
  });

  const activeCount   = list.filter(p => p.status === 'active').length;
  const expiredCount  = list.filter(p => p.status === 'expired').length;
  const expiringSoon  = list.filter(p => p.status === 'active' && daysUntil(p.valid_until) <= 30).length;
  const pendingCount  = list.filter(p => p.status === 'pending').length;

  const onSubmit = async (data: NewPoaForm) => {
    try {
      await createPoa.mutateAsync({
        client_id: data.client_id || undefined,
        cnpj_grantor: data.cnpj_grantor,
        cnpj_attorney: data.cnpj_attorney,
        valid_until: data.valid_until || undefined,
        provider: data.provider,
        notes: data.notes || undefined,
      });
      toast.success('Procuração cadastrada com sucesso!');
      setOpenModal(false);
      reset();
    } catch (err) {
      toast.error(getApiErrorMessage(err, 'Erro ao cadastrar procuração.'));
    }
  };

  const handleRevoke = async (id: string) => {
    if (!window.confirm('Confirma a revogação desta procuração?')) return;
    try {
      await revokePoa.mutateAsync({ id, reason: 'Revogação manual pelo operador.' });
      toast.success('Procuração revogada.');
    } catch (err) {
      toast.error(getApiErrorMessage(err, 'Erro ao revogar procuração.'));
    }
  };

  if (isLoading) return <PageSpinner />;

  return (
    <FeatureGate feature="feature_powers_of_attorney">
      <div className="space-y-6 p-6">
        <PageHeader
          title="Procurações"
          subtitle="Gerencie as procurações digitais de todos os clientes."
          icon={<FileText className="h-5 w-5" />}
          actions={
            <Button onClick={() => setOpenModal(true)} className="flex items-center gap-2">
              <Plus className="h-4 w-4" />
              Nova procuração
            </Button>
          }
        />

        {error && (
          <WarningPanel
            title="Módulo em implantação"
            description="O módulo de procurações está sendo ativado. Estará disponível em breve."
            variant="warning"
          />
        )}

        {!error && expiredCount > 0 && (
          <WarningPanel
            title={`${expiredCount} procuração${expiredCount > 1 ? 'ões' : ''} vencida${expiredCount > 1 ? 's' : ''}`}
            description="Procurações vencidas bloqueiam consultas e-CAC, emissão de guias e caixa postal fiscal."
            variant="danger"
          />
        )}
        {!error && expiringSoon > 0 && (
          <WarningPanel
            title={`${expiringSoon} procuração${expiringSoon > 1 ? 'ões' : ''} vencendo em 30 dias`}
            description="Renove antes do vencimento para evitar interrupção dos serviços."
            variant="warning"
          />
        )}

        {/* Metrics */}
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <MetricCard title="Ativas"          value={activeCount}   icon={<CheckCircle2 className="h-4 w-4" />} variant="success"  />
          <MetricCard title="Vencendo em 30d" value={expiringSoon}  icon={<Clock         className="h-4 w-4" />} variant="warning"  />
          <MetricCard title="Vencidas"        value={expiredCount}  icon={<AlertTriangle className="h-4 w-4" />} variant="danger"   />
          <MetricCard title="Pendentes"       value={pendingCount}  icon={<Clock         className="h-4 w-4" />} variant="default"  />
        </div>

        {/* Filters */}
        <div className="flex flex-wrap gap-3">
          <div className="relative flex-1 min-w-[200px]">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <input
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder="Buscar por cliente ou CNPJ..."
              className="w-full rounded-lg border border-border bg-card py-2 pl-9 pr-4 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/40"
            />
          </div>
          <select
            value={statusFilter}
            onChange={e => setStatusFilter(e.target.value)}
            className="rounded-lg border border-border bg-card px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40"
          >
            {STATUS_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
        </div>

        {/* Table */}
        {filtered.length === 0 ? (
          <EmptyState
            icon={<FileText className="h-6 w-6" />}
            title="Nenhuma procuração encontrada"
            description="Cadastre procurações para habilitar consultas e-CAC e emissão de guias."
            action={
              <Button onClick={() => setOpenModal(true)}>
                Cadastrar procuração
              </Button>
            }
          />
        ) : (
          <div className="overflow-hidden rounded-xl border border-border">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border bg-muted/30">
                  <th className="px-4 py-3 text-left text-xs font-semibold text-muted-foreground">Cliente / CNPJ</th>
                  <th className="hidden px-4 py-3 text-left text-xs font-semibold text-muted-foreground lg:table-cell">Provider</th>
                  <th className="hidden px-4 py-3 text-left text-xs font-semibold text-muted-foreground sm:table-cell">Validade</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-muted-foreground">Status</th>
                  <th className="px-4 py-3 text-right text-xs font-semibold text-muted-foreground">Ações</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map(pow => {
                  const days = daysUntil(pow.valid_until);
                  const expiring = pow.status === 'active' && days <= 30;
                  const client = clients?.find(c => c.id === pow.client_id);
                  return (
                    <tr key={pow.id} className="border-b border-border/50 last:border-0 transition-colors hover:bg-muted/20">
                      <td className="px-4 py-3">
                        <div>
                          <p className="font-medium text-foreground">{client?.name ?? pow.cnpj_grantor}</p>
                          <p className="text-xs text-muted-foreground">{pow.cnpj_grantor}</p>
                          {pow.notes && <p className="text-xs text-warning mt-0.5">{pow.notes}</p>}
                        </div>
                      </td>
                      <td className="hidden px-4 py-3 text-xs text-muted-foreground lg:table-cell">{pow.provider}</td>
                      <td className="hidden px-4 py-3 sm:table-cell">
                        <div>
                          <p className={cn('text-xs', expiring ? 'text-warning font-semibold' : 'text-muted-foreground')}>
                            {pow.valid_until ? new Date(pow.valid_until).toLocaleDateString('pt-BR') : '—'}
                          </p>
                          {expiring && <p className="text-[10px] text-warning/80">em {days} dias</p>}
                        </div>
                      </td>
                      <td className="px-4 py-3"><StatusBadge status={pow.status} /></td>
                      <td className="px-4 py-3">
                        <div className="flex items-center justify-end gap-2">
                          {pow.status === 'active' && (
                            <button
                              onClick={() => handleRevoke(pow.id)}
                              className="rounded-lg border border-destructive/30 px-2.5 py-1 text-xs font-medium text-destructive hover:bg-destructive/10 transition-colors"
                            >
                              Revogar
                            </button>
                          )}
                          {(pow.status === 'expired' || expiring) && (
                            <button
                              className="rounded-lg border border-warning/30 px-2.5 py-1 text-xs font-medium text-warning hover:bg-warning/10 transition-colors"
                              onClick={() => toast.info('Fluxo de renovação em breve.')}
                            >
                              <RefreshCw className="h-3 w-3 inline mr-1" />
                              Renovar
                            </button>
                          )}
                          <ChevronRight className="h-3.5 w-3.5 text-muted-foreground" />
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* New PoA Modal */}
      <Dialog open={openModal} onClose={() => { setOpenModal(false); reset(); }} title="Nova Procuração">
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <FormField label="Cliente" htmlFor="client_id">
            <select
              id="client_id"
              {...register('client_id')}
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              <option value="">Selecione o cliente...</option>
              {clients?.map(c => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </select>
          </FormField>

          <div className="grid grid-cols-2 gap-3">
            <FormField label="CNPJ Outorgante" htmlFor="cnpj_grantor">
              <Input id="cnpj_grantor" placeholder="00.000.000/0001-00" {...register('cnpj_grantor', { required: true })} />
            </FormField>
            <FormField label="CNPJ Outorgado" htmlFor="cnpj_attorney">
              <Input id="cnpj_attorney" placeholder="00.000.000/0001-00" {...register('cnpj_attorney', { required: true })} />
            </FormField>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <FormField label="Válida até" htmlFor="valid_until">
              <Input type="date" id="valid_until" {...register('valid_until')} />
            </FormField>
            <FormField label="Provider" htmlFor="provider">
              <Input id="provider" {...register('provider')} />
            </FormField>
          </div>

          <FormField label="Observações" htmlFor="notes">
            <Input id="notes" placeholder="Opcional..." {...register('notes')} />
          </FormField>

          <div className="flex justify-end gap-3 pt-2">
            <Button type="button" variant="outline" onClick={() => { setOpenModal(false); reset(); }}>
              Cancelar
            </Button>
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? 'Salvando...' : 'Cadastrar'}
            </Button>
          </div>
        </form>
      </Dialog>
    </FeatureGate>
  );
}

export default PowersOfAttorneyPage;
