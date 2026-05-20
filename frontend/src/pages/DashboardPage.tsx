import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { CalendarClock, ReceiptText, ShieldAlert, UsersRound } from 'lucide-react';
import { dateBR, moneyBRL, useDashboardOverview } from '@/lib/hooks/useOperations';

export function DashboardPage() {
  const { data, isLoading, isError } = useDashboardOverview();

  const stats = [
    {
      title: 'Clientes ativos',
      value: data?.active_clients ?? 0,
      detail: 'Carteira em operação',
      icon: UsersRound,
      color: 'text-blue-600',
    },
    {
      title: 'Prazos pendentes',
      value: data?.pending_deadlines ?? 0,
      detail: `${data?.overdue_deadlines ?? 0} atrasados`,
      icon: CalendarClock,
      color: 'text-red-600',
    },
    {
      title: 'Certificados 30 dias',
      value: data?.certificates_expiring_30d ?? 0,
      detail: 'Renovações próximas',
      icon: ShieldAlert,
      color: 'text-amber-600',
    },
    {
      title: 'A receber',
      value: moneyBRL(data?.receivables_amount_open),
      detail: `${data?.overdue_receivables ?? 0} cobranças em atraso`,
      icon: ReceiptText,
      color: 'text-emerald-600',
    },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold md:text-3xl">Dashboard</h1>
        <p className="text-muted-foreground">Visão geral da operação contábil do escritório.</p>
      </div>

      {isError && (
        <Card className="border-destructive/40">
          <CardContent className="pt-6 text-sm text-destructive">
            Não foi possível carregar os dados operacionais agora.
          </CardContent>
        </Card>
      )}

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {stats.map((stat) => (
          <Card key={stat.title}>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">{stat.title}</CardTitle>
              <stat.icon className={`h-4 w-4 ${stat.color}`} />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{isLoading ? '...' : stat.value}</div>
              <p className="mt-1 text-xs text-muted-foreground">{stat.detail}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="text-base">Próximos prazos</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {(data?.upcoming_deadlines ?? []).length === 0 && (
              <p className="text-sm text-muted-foreground">
                Nenhum prazo futuro cadastrado. Cadastre o primeiro prazo em Agenda e Prazos.
              </p>
            )}
            {(data?.upcoming_deadlines ?? []).map((deadline) => (
              <div
                key={deadline.id}
                className="flex items-start justify-between gap-3 rounded-md border p-3"
              >
                <div className="min-w-0">
                  <p className="font-medium">{deadline.title}</p>
                  <p className="truncate text-sm text-muted-foreground">{deadline.category}</p>
                </div>
                <div className="text-right">
                  <p className="text-sm font-medium">{dateBR(deadline.due_date)}</p>
                  <Badge variant={deadline.priority === 'high' ? 'error' : 'warning'}>
                    {deadline.priority === 'high' ? 'Alta' : 'Acompanhar'}
                  </Badge>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Risco financeiro</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="rounded-md border p-3">
              <p className="text-sm text-muted-foreground">Valor vencido</p>
              <p className="mt-1 text-2xl font-bold">{moneyBRL(data?.receivables_amount_overdue)}</p>
            </div>
            <div className="rounded-md border p-3">
              <p className="text-sm text-muted-foreground">Recebíveis em aberto</p>
              <p className="mt-1 text-2xl font-bold">{data?.open_receivables ?? 0}</p>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
