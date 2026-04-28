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
        <h1 className="text-3xl font-bold">Configurações</h1>
        <p className="text-muted-foreground">Gerencie suas informações e preferências</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Perfil do Usuário</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <label className="text-sm font-medium text-muted-foreground">Nome Completo</label>
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
          <CardTitle>Informações do Tenant</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <label className="text-sm font-medium text-muted-foreground">Tenant ID</label>
            <div className="flex items-center gap-2">
              <code className="bg-muted px-3 py-2 rounded text-sm flex-1">{tenantId}</code>
            </div>
            <p className="text-xs text-muted-foreground">
              Use este ID para integrar o widget em seu site
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
