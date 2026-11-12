import { useState } from 'react';
import {
  FileText, Plus, Search, AlertTriangle, CheckCircle2,
  Clock, XCircle, RefreshCw,
} from 'lucide-react';
import { PageHeader } from '@/components/ui/PageHeader';
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
import { ProxyStatusBadge } from '@/features/ecac/components/ProxyStatusBadge';
import {
  usePowersOfAttorney,
  useCreatePowerOfAttorney,
  useRevokePowerOfAttorney,
  useRenewPowerOfAttorney,
  daysUntil,
  effectiveStatus,
  onlyDigits,
  renewalDefaults,
  todayISO,
  type PowerOfAttorney,
} from '@/features/powers-of-attorney/api';

const STATUS_OPTIONS = [
  { value: 'all', label: 'Todos os status' },
  { value: 'ativa', label: 'Ativas' },
  { value: 'vencida', label: 'Vencidas' },
  { value: 'revogada', label: 'Revogadas' },
];

type NewPoaForm = {
  client_id: string;
  outorgante_cpf_cnpj: string;
  outorgante_nome: string;
  procurador_cpf: string;
  tipo: string;
  data_inicio: string;
  data_validade: string;
};

const emptyForm = (): NewPoaForm => ({
  client_id: '',
  outorgante_cpf_cnpj: '',
  outorgante_nome: '',
  procurador_cpf: '',
  tipo: 'e-CAC',
  data_inicio: todayISO(),
  data_validade: '',
});

function dateBR(iso: string | null | undefined): string {
  if (!iso) return '—';
  const [y, m, d] = iso.slice(0, 10).split('-');
  return `${d}/${m}/${y}`;
}

export function PowersOfAttorneyPage() {
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [openModal, setOpenModal] = useState(false);
  /** Procuração sendo renovada: ao salvar, a nova é criada e esta é revogada. */
  const [renewing, setRenewing] = useState<PowerOfAttorney | null>(null);

  const { data: powers, isLoading, error } = usePowersOfAttorney();
  const { data: clients } = useClients();
  const createPoa = useCreatePowerOfAttorney();
  const revokePoa = useRevokePowerOfAttorney();
  const renewPoa = useRenewPowerOfAttorney();

  const { register, handleSubmit, reset, setValue, formState: { isSubmitting, errors } } = useForm<NewPoaForm>({
    defaultValues: emptyForm(),
  });

  const today = todayISO();
  const list = (powers ?? []).map(p => ({
    poa: p,
    status: effectiveStatus(p, today),
    days: daysUntil(p.data_validade, today),
  }));

  const filtered = list.filter(({ poa, status }) => {
    if (statusFilter !== 'all' && status !== statusFilter) return false;
    if (!search) return true;
    const client = clients?.find(c => c.id === poa.client_id);
    const name = (client?.name ?? poa.outorgante_nome ?? '').toLowerCase();
    const q = search.toLowerCase();
    const qDigits = onlyDigits(search);
    return name.includes(q) || (qDigits !== '' && poa.outorgante_cpf_cnpj.includes(qDigits));
  });

  const isExpiringSoon = (status: string, days: number | null) =>
    status === 'ativa' && days !== null && days <= 30;
  const activeCount   = list.filter(p => p.status === 'ativa').length;
  const expiredCount  = list.filter(p => p.status === 'vencida').length;
  const expiringSoon  = list.filter(p => isExpiringSoon(p.status, p.days)).length;
  const revokedCount  = list.filter(p => p.status === 'revogada').length;

  const closeModal = () => {
    setOpenModal(false);
    setRenewing(null);
    reset(emptyForm());
  };

  const openNew = () => {
    setRenewing(null);
    reset(emptyForm());
    setOpenModal(true);
  };

  const openRenew = (poa: PowerOfAttorney) => {
    setRenewing(poa);
    reset(renewalDefaults(poa, today));
    setOpenModal(true);
  };

  const onClientChange = (clientId: string) => {
    const client = clients?.find(c => c.id === clientId);
    if (!client) return;
    setValue('outorgante_cpf_cnpj', onlyDigits(client.document));
    setValue('outorgante_nome', client.name);
  };

  const onSubmit = async (data: NewPoaForm) => {
    const payload = {
      client_id: data.client_id || undefined,
      outorgante_cpf_cnpj: onlyDigits(data.outorgante_cpf_cnpj),
      outorgante_nome: data.outorgante_nome || undefined,
      procurador_cpf: onlyDigits(data.procurador_cpf),
      tipo: data.tipo || 'e-CAC',
      data_inicio: data.data_inicio || undefined,
      data_validade: data.data_validade || undefined,
    };
    try {
      if (renewing) {
        await renewPoa.mutateAsync({ oldId: renewing.id, data: payload });
        toast.success('Procuração renovada. A anterior foi revogada.');
      } else {
        await createPoa.mutateAsync(payload);
        toast.success('Procuração cadastrada com sucesso!');
      }
      closeModal();
    } catch (err) {
      toast.error(getApiErrorMessage(err, 'Erro ao salvar procuração.'));
    }
  };

  const handleRevoke = async (id: string) => {
    if (!window.confirm('Confirma a revogação desta procuração?')) return;
    try {
      await revokePoa.mutateAsync(id);
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
            <Button onClick={openNew} className="flex items-center gap-2">
              <Plus className="h-4 w-4" />
              Nova procuração
            </Button>
          }
        />

        {error && (
          <WarningPanel
            title="Não foi possível carregar as procurações"
            description={getApiErrorMessage(error, 'Verifique sua conexão e tente novamente.')}
            variant="danger"
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
          <MetricCard title="Revogadas"       value={revokedCount}  icon={<XCircle       className="h-4 w-4" />} variant="default"  />
        </div>

        {/* Filters */}
        <div className="flex flex-wrap gap-3">
          <div className="relative flex-1 min-w-[200px]">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <input
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder="Buscar por cliente ou CPF/CNPJ do outorgante..."
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
              <Button onClick={openNew}>
                Cadastrar procuração
              </Button>
            }
          />
        ) : (
          <div className="overflow-hidden rounded-xl border border-border">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border bg-muted/30">
                  <th className="px-4 py-3 text-left text-xs font-semibold text-muted-foreground">Cliente / Outorgante</th>
                  <th className="hidden px-4 py-3 text-left text-xs font-semibold text-muted-foreground lg:table-cell">Procurador (CPF)</th>
                  <th className="hidden px-4 py-3 text-left text-xs font-semibold text-muted-foreground sm:table-cell">Validade</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-muted-foreground">Status</th>
                  <th className="px-4 py-3 text-right text-xs font-semibold text-muted-foreground">Ações</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map(({ poa: pow, status, days }) => {
                  const expiring = isExpiringSoon(status, days);
                  const client = clients?.find(c => c.id === pow.client_id);
                  return (
                    <tr key={pow.id} className="border-b border-border/50 last:border-0 transition-colors hover:bg-muted/20">
                      <td className="px-4 py-3">
                        <div>
                          <p className="font-medium text-foreground">{client?.name ?? pow.outorgante_nome ?? pow.outorgante_cpf_cnpj}</p>
                          <p className="text-xs text-muted-foreground">{pow.outorgante_cpf_cnpj}{pow.tipo ? ` · ${pow.tipo}` : ''}</p>
                        </div>
                      </td>
                      <td className="hidden px-4 py-3 text-xs text-muted-foreground lg:table-cell">{pow.procurador_cpf}</td>
                      <td className="hidden px-4 py-3 sm:table-cell">
                        <div>
                          <p className={cn('text-xs', expiring ? 'text-warning font-semibold' : 'text-muted-foreground')}>
                            {dateBR(pow.data_validade)}
                          </p>
                          {expiring && <p className="text-[10px] text-warning/80">{days === 0 ? 'vence hoje' : `em ${days} dias`}</p>}
                        </div>
                      </td>
                      <td className="px-4 py-3"><ProxyStatusBadge status={status} /></td>
                      <td className="px-4 py-3">
                        <div className="flex items-center justify-end gap-2">
                          {(status === 'vencida' || expiring) && (
                            <button
                              className="rounded-lg border border-warning/30 px-2.5 py-1 text-xs font-medium text-warning hover:bg-warning/10 transition-colors"
                              onClick={() => openRenew(pow)}
                              title="Cadastrar a nova procuração e revogar esta"
                            >
                              <RefreshCw className="h-3 w-3 inline mr-1" />
                              Renovar
                            </button>
                          )}
                          {status !== 'revogada' && (
                            <button
                              onClick={() => handleRevoke(pow.id)}
                              className="rounded-lg border border-destructive/30 px-2.5 py-1 text-xs font-medium text-destructive hover:bg-destructive/10 transition-colors"
                            >
                              Revogar
                            </button>
                          )}
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

      {/* New / renew PoA Modal */}
      <Dialog open={openModal} onClose={closeModal} title={renewing ? 'Renovar procuração' : 'Nova procuração'}>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          {renewing && (
            <p className="text-xs text-muted-foreground">
              Ao salvar, a nova procuração é cadastrada e a anterior (validade {dateBR(renewing.data_validade)}) é revogada.
            </p>
          )}
          <FormField label="Cliente" htmlFor="client_id">
            <select
              id="client_id"
              {...register('client_id', { onChange: e => onClientChange(e.target.value) })}
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              <option value="">Selecione o cliente...</option>
              {clients?.map(c => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </select>
          </FormField>

          <div className="grid grid-cols-2 gap-3">
            <FormField label="CPF/CNPJ do outorgante" htmlFor="outorgante_cpf_cnpj" error={errors.outorgante_cpf_cnpj?.message}>
              <Input
                id="outorgante_cpf_cnpj"
                placeholder="00.000.000/0001-00"
                {...register('outorgante_cpf_cnpj', {
                  validate: v => [11, 14].includes(onlyDigits(v).length) || 'Informe um CPF (11) ou CNPJ (14 dígitos).',
                })}
              />
            </FormField>
            <FormField label="CPF do procurador" htmlFor="procurador_cpf" error={errors.procurador_cpf?.message}>
              <Input
                id="procurador_cpf"
                placeholder="000.000.000-00"
                {...register('procurador_cpf', {
                  validate: v => onlyDigits(v).length === 11 || 'Informe o CPF do procurador (11 dígitos).',
                })}
              />
            </FormField>
          </div>

          <FormField label="Nome do outorgante" htmlFor="outorgante_nome">
            <Input id="outorgante_nome" placeholder="Opcional..." {...register('outorgante_nome')} />
          </FormField>

          <div className="grid grid-cols-3 gap-3">
            <FormField label="Tipo" htmlFor="tipo">
              <Input id="tipo" {...register('tipo')} />
            </FormField>
            <FormField label="Início" htmlFor="data_inicio">
              <Input type="date" id="data_inicio" {...register('data_inicio')} />
            </FormField>
            <FormField label="Válida até" htmlFor="data_validade">
              <Input type="date" id="data_validade" {...register('data_validade')} />
            </FormField>
          </div>

          <div className="flex justify-end gap-3 pt-2">
            <Button type="button" variant="outline" onClick={closeModal}>
              Cancelar
            </Button>
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? 'Salvando...' : renewing ? 'Renovar' : 'Cadastrar'}
            </Button>
          </div>
        </form>
      </Dialog>
    </FeatureGate>
  );
}

export default PowersOfAttorneyPage;
