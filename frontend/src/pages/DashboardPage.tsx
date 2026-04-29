import { useAnalytics } from '@/lib/hooks/useAnalytics';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { MessageSquare, Coins, DollarSign } from 'lucide-react';

export function DashboardPage() {
  const { dashboardData } = useAnalytics();

  if (dashboardData.isLoading) {
    return <div className="flex items-center justify-center h-full">Carregando...</div>;
  }

  const data = dashboardData.data;

  const stats = [
    {
      title: 'Total de Sessões',
      value: data?.sessions?.total_sessions ?? 0,
      icon: MessageSquare,
      color: 'text-blue-600',
    },
    {
      title: 'Total de Mensagens',
      value: data?.sessions?.total_messages ?? 0,
      icon: MessageSquare,
      color: 'text-green-600',
    },
    {
      title: 'Total de Tokens',
      value: (data?.token_usage?.total_tokens ?? 0).toLocaleString(),
      icon: Coins,
      color: 'text-purple-600',
    },
    {
      title: 'Custo Total (USD)',
      value: `$${(data?.token_usage?.total_cost_usd ?? 0).toFixed(4)}`,
      icon: DollarSign,
      color: 'text-orange-600',
    },
  ];

  const chartData = data?.daily_metrics?.map((metric) => ({
    date: new Date(metric.date).toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' }),
    sessões: metric.total_sessions,
    mensagens: metric.total_messages,
  })) ?? [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Dashboard</h1>
        <p className="text-muted-foreground">Visão geral do seu uso da plataforma</p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {stats.map((stat) => (
          <Card key={stat.title}>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">{stat.title}</CardTitle>
              <stat.icon className={`h-4 w-4 ${stat.color}`} />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stat.value}</div>
            </CardContent>
          </Card>
        ))}
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Uso nos Últimos 30 Dias</CardTitle>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" />
              <YAxis />
              <Tooltip />
              <Bar dataKey="sessões" fill="hsl(var(--primary))" />
              <Bar dataKey="mensagens" fill="hsl(var(--muted))" />
            </BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Análise de Sessões</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Total de Sessões</span>
              <span className="font-medium">{data?.sessions?.total_sessions ?? 0}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Total de Mensagens</span>
              <span className="font-medium">{data?.sessions?.total_messages ?? 0}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Média de Mensagens/Sessão</span>
              <span className="font-medium">
                {(data?.sessions?.avg_messages_per_session ?? 0).toFixed(1)}
              </span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Base de Conhecimento</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Total de Documentos</span>
              <span className="font-medium">{data?.documents?.total_documents ?? 0}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Total de Chunks</span>
              <span className="font-medium">{data?.documents?.total_chunks ?? 0}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Processados</span>
              <span className="font-medium text-green-600">
                {data?.documents?.by_status?.['processed'] ?? 0}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Pendentes</span>
              <span className="font-medium text-yellow-600">
                {data?.documents?.by_status?.['pending'] ?? 0}
              </span>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
