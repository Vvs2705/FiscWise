import { useMemo } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { AlertTriangle, CheckCircle2, Laptop, RefreshCw, RotateCcw, Trash2 } from 'lucide-react';
import { toast } from 'sonner';
import { PageHeader } from '@/components/ui/PageHeader';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { InstallAppPrompt } from '@/components/InstallAppPrompt';
import { usePermission } from '@/lib/hooks/usePermission';
import { getApiErrorMessage } from '@/lib/api';
import {
  useConflicts,
  useCurrentDeviceId,
  useLocalDb,
  usePendingChanges,
  useSyncNow,
  useSyncStatus,
} from '@/lib/offline/hooks';
import { ENTITY_LABEL, SYNC_ENTITIES, type OutboxEvent, type SyncEntityType } from '@/lib/offline/db';
import { discardEvent, resolveConflictKeep, resolveConflictRestoreServer } from '@/lib/offline/engine';
import { retryEvent } from '@/lib/offline/outbox';
import { listSyncDevices, revokeSyncDevice } from '@/lib/offline/transport';
import { cn } from '@/lib/utils';

const OPERATION_LABEL: Record<OutboxEvent['operation'], string> = {
  create: 'Criação',
  update: 'Edição',
  delete: 'Desativação',
  emit_requested: 'Pedido de transmissão',
};

function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return 'nunca';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '—';
  return d.toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' });
}

function formatValue(v: unknown): string {
  if (v === null || v === undefined || v === '') return '(vazio)';
  if (typeof v === 'object') return JSON.stringify(v);
  return String(v);
}

const TONE_BADGE = { online: 'success', offline: 'default', syncing: 'info', error: 'error' } as const;

export function SyncPage() {
  const status = useSyncStatus();
  const { syncNow, running } = useSyncNow();
  const db = useLocalDb();
  const pending = usePendingChanges();
  const conflicts = useConflicts();
  const deviceId = useCurrentDeviceId();
  const { hasRole } = usePermission();
  const canManageDevices = hasRole('admin');
  const queryClient = useQueryClient();

  const grouped = useMemo(() => {
    const map = new Map<SyncEntityType, OutboxEvent[]>();
    for (const e of pending ?? []) {
      const list = map.get(e.entity_type) ?? [];
      list.push(e);
      map.set(e.entity_type, list);
    }
    return SYNC_ENTITIES.filter((e) => map.has(e)).map((e) => ({ entity: e, events: map.get(e)! }));
  }, [pending]);

  const devices = useQuery({
    queryKey: ['sync-devices'],
    queryFn: listSyncDevices,
    enabled: canManageDevices && !status.isOffline,
    retry: false,
  });

  const revoke = useMutation({
    mutationFn: revokeSyncDevice,
    onSuccess: () => {
      toast.success('Dispositivo revogado. Os dados locais dele serão apagados no próximo contato.');
      void queryClient.invalidateQueries({ queryKey: ['sync-devices'] });
    },
    onError: (err) => toast.error(getApiErrorMessage(err, 'Não foi possível revogar o dispositivo.')),
  });

  const handleSyncNow = async () => {
    const res = await syncNow();
    if (!res) toast.error('Sincronização indisponível: entre novamente ou verifique a conexão.');
    else if (res.status === 'ok') toast.success('Sincronização concluída.');
    else if (res.status === 'offline') toast.error('Sem conexão. As alterações continuam guardadas neste dispositivo.');
    else if (res.status === 'error') toast.error(res.error ?? 'Erro na sincronização.');
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Sincronização"
        subtitle="Alterações feitas sem internet ficam guardadas neste dispositivo e são enviadas quando a conexão voltar."
        icon={<RefreshCw className="h-5 w-5" />}
        actions={
          <Button onClick={handleSyncNow} disabled={running || status.phase !== 'idle'} className="gap-2">
            <RefreshCw className={cn('h-4 w-4', (running || status.phase !== 'idle') && 'animate-spin')} aria-hidden="true" />
            Sincronizar agora
          </Button>
        }
      />

      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm text-muted-foreground">Estado</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <Badge variant={TONE_BADGE[status.tone]}>{status.label}</Badge>
            {status.lastError && status.tone !== 'online' && (
              <p className="text-xs text-muted-foreground">{status.lastError}</p>
            )}
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm text-muted-foreground">Última sincronização</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-lg font-semibold">{formatDateTime(status.lastSyncAt)}</p>
            <p className="text-xs text-muted-foreground">
              {status.pending} {status.pending === 1 ? 'pendente' : 'pendentes'} · {status.errors} com erro ·{' '}
              {status.conflicts} {status.conflicts === 1 ? 'conflito' : 'conflitos'}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm text-muted-foreground">Este dispositivo</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <p className="flex items-center gap-2 text-sm">
              <Laptop className="h-4 w-4 shrink-0 text-muted-foreground" aria-hidden="true" />
              <span className="break-all font-mono text-xs">{deviceId ?? 'ainda não registrado'}</span>
            </p>
            <InstallAppPrompt />
          </CardContent>
        </Card>
      </div>

      {/* Pendências por entidade */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Alterações não enviadas</CardTitle>
        </CardHeader>
        <CardContent>
          {!db ? (
            <p className="text-sm text-muted-foreground">Banco local indisponível nesta sessão.</p>
          ) : grouped.length === 0 ? (
            <p className="flex items-center gap-2 text-sm text-muted-foreground">
              <CheckCircle2 className="h-4 w-4 text-success" aria-hidden="true" />
              Tudo enviado. Nenhuma alteração pendente.
            </p>
          ) : (
            <div className="space-y-5">
              {grouped.map(({ entity, events }) => (
                <section key={entity} aria-label={ENTITY_LABEL[entity]}>
                  <h3 className="mb-2 text-sm font-semibold">
                    {ENTITY_LABEL[entity]} <span className="text-muted-foreground">({events.length})</span>
                  </h3>
                  <ul className="divide-y rounded-md border">
                    {events.map((e) => (
                      <li key={e.id} className="flex flex-col gap-2 p-3 text-sm sm:flex-row sm:items-center sm:justify-between">
                        <div className="min-w-0">
                          <p className="font-medium">
                            {OPERATION_LABEL[e.operation]}{' '}
                            <span className="font-normal text-muted-foreground">· {formatDateTime(e.created_at)}</span>
                          </p>
                          <p className="truncate text-xs text-muted-foreground">
                            {typeof e.payload.name === 'string'
                              ? e.payload.name
                              : typeof e.payload.title === 'string'
                                ? e.payload.title
                                : typeof e.payload.description === 'string'
                                  ? e.payload.description
                                  : e.entity_id}
                          </p>
                          {e.status === 'error' && (
                            <p className="mt-1 flex items-start gap-1 text-xs text-destructive">
                              <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden="true" />
                              {e.last_error ?? 'Rejeitado pelo servidor.'}
                            </p>
                          )}
                          {e.status === 'pending' && e.last_error && (
                            <p className="mt-1 text-xs text-muted-foreground">
                              Nova tentativa automática. Último erro: {e.last_error}
                            </p>
                          )}
                        </div>
                        <div className="flex shrink-0 items-center gap-2">
                          <Badge variant={e.status === 'error' ? 'error' : e.status === 'syncing' ? 'info' : 'warning'}>
                            {e.status === 'error' ? 'Erro' : e.status === 'syncing' ? 'Enviando' : 'Não enviado'}
                          </Badge>
                          {e.status === 'error' && (
                            <>
                              <Button
                                size="sm"
                                variant="outline"
                                className="gap-1"
                                onClick={async () => {
                                  await retryEvent(db, e.id);
                                  void syncNow();
                                }}
                              >
                                <RotateCcw className="h-3.5 w-3.5" aria-hidden="true" />
                                Tentar de novo
                              </Button>
                              <Button
                                size="sm"
                                variant="ghost"
                                className="gap-1 text-destructive hover:text-destructive"
                                onClick={async () => {
                                  if (!window.confirm('Descartar esta alteração? A versão do servidor volta na próxima sincronização.')) return;
                                  await discardEvent(db, e.id);
                                  toast.success('Alteração descartada.');
                                }}
                              >
                                <Trash2 className="h-3.5 w-3.5" aria-hidden="true" />
                                Descartar
                              </Button>
                            </>
                          )}
                        </div>
                      </li>
                    ))}
                  </ul>
                </section>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Conflitos */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Conflitos para revisar</CardTitle>
        </CardHeader>
        <CardContent>
          {(conflicts ?? []).length === 0 ? (
            <p className="text-sm text-muted-foreground">Nenhum conflito. Quando dois dispositivos editam o mesmo campo, ele aparece aqui.</p>
          ) : (
            <ul className="space-y-4">
              {(conflicts ?? []).map((c) => (
                <li key={c.id} className="rounded-md border p-3">
                  <p className="text-sm font-medium">
                    {ENTITY_LABEL[c.entity_type]} <span className="text-muted-foreground">· {formatDateTime(c.created_at)}</span>
                  </p>
                  <p className="mb-2 text-xs text-muted-foreground">
                    Sua alteração foi gravada por último e substituiu o valor abaixo, que estava no servidor.
                  </p>
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs">
                      <thead>
                        <tr className="text-muted-foreground">
                          <th className="py-1 pr-3 font-medium">Campo</th>
                          <th className="py-1 pr-3 font-medium">Valor anterior (servidor)</th>
                          <th className="py-1 font-medium">Valor gravado (este dispositivo)</th>
                        </tr>
                      </thead>
                      <tbody>
                        {Object.entries(c.fields_overwritten).map(([field, v]) => (
                          <tr key={field} className="border-t">
                            <td className="py-1 pr-3 font-mono">{field}</td>
                            <td className="py-1 pr-3">{formatValue(v.server)}</td>
                            <td className="py-1">{formatValue(v.client)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  {db && (
                    <div className="mt-3 flex flex-wrap gap-2">
                      <Button size="sm" variant="outline" onClick={() => void resolveConflictKeep(db, c.id)}>
                        Manter como está
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={async () => {
                          await resolveConflictRestoreServer(db, c.id);
                          toast.success('Valor do servidor restaurado. Será enviado na próxima sincronização.');
                        }}
                      >
                        Restaurar valor do servidor
                      </Button>
                    </div>
                  )}
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>

      {/* Dispositivos (dono/admin) */}
      {canManageDevices && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Dispositivos</CardTitle>
          </CardHeader>
          <CardContent>
            {status.isOffline ? (
              <p className="text-sm text-muted-foreground">Precisa de internet para listar e revogar dispositivos.</p>
            ) : devices.isLoading ? (
              <p className="text-sm text-muted-foreground">Carregando…</p>
            ) : devices.isError ? (
              <p className="text-sm text-destructive">{getApiErrorMessage(devices.error, 'Não foi possível carregar os dispositivos.')}</p>
            ) : (devices.data ?? []).length === 0 ? (
              <p className="text-sm text-muted-foreground">Nenhum dispositivo registrado.</p>
            ) : (
              <ul className="divide-y rounded-md border">
                {(devices.data ?? []).map((d) => (
                  <li key={d.id} className="flex flex-col gap-2 p-3 text-sm sm:flex-row sm:items-center sm:justify-between">
                    <div className="min-w-0">
                      <p className="font-medium">
                        {d.name}
                        {d.id === deviceId && <span className="ml-2 text-xs text-primary">(este dispositivo)</span>}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        Último acesso: {formatDateTime(d.last_seen_at)} · versão {d.app_version}
                      </p>
                    </div>
                    {d.revoked_at ? (
                      <Badge variant="error">Revogado em {formatDateTime(d.revoked_at)}</Badge>
                    ) : (
                      <Button
                        size="sm"
                        variant="destructive"
                        disabled={revoke.isPending}
                        onClick={() => {
                          const msg =
                            d.id === deviceId
                              ? 'Revogar ESTE dispositivo? O banco local será apagado e você voltará para o login.'
                              : `Revogar "${d.name}"? O banco local dele será apagado no próximo contato.`;
                          if (window.confirm(msg)) revoke.mutate(d.id);
                        }}
                      >
                        Revogar
                      </Button>
                    )}
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}

export default SyncPage;
