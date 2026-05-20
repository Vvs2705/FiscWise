import { useAuthStore } from '@/stores/authStore';
import { getTenantId } from '@/lib/auth';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';

export function SettingsPage() {
  const { user } = useAuthStore();
  const tenantId = getTenantId();

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold md:text-3xl">Configurações</h1>
        <p className="text-muted-foreground">
          Ajuste dados do usuário, escritório e preferências operacionais.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Perfil do usuário</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <label className="text-sm font-medium text-muted-foreground">Nome completo</label>
            <div className="text-lg">{user?.full_name}</div>
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium text-muted-foreground">Email</label>
            <div className="text-lg">{user?.email}</div>
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium text-muted-foreground">Função</label>
            <div>
              <Badge>{user?.role}</Badge>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Informações do escritório</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <label className="text-sm font-medium text-muted-foreground">Identificador interno</label>
            <div className="flex items-center gap-2">
              <code className="flex-1 rounded bg-muted px-3 py-2 text-sm">{tenantId}</code>
            </div>
            <p className="text-xs text-muted-foreground">
              Referência usada para separar dados e permissões do escritório.
            </p>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Preferências operacionais</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-3">
          <div className="rounded-md border p-4">
            <p className="font-medium">Alertas de prazo</p>
            <p className="mt-1 text-sm text-muted-foreground">Avisar 5 dias antes do vencimento.</p>
          </div>
          <div className="rounded-md border p-4">
            <p className="font-medium">Documentos pendentes</p>
            <p className="mt-1 text-sm text-muted-foreground">Revisão diária da esteira documental.</p>
          </div>
          <div className="rounded-md border p-4">
            <p className="font-medium">Certificados digitais</p>
            <p className="mt-1 text-sm text-muted-foreground">Priorizar renovações com até 30 dias.</p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
