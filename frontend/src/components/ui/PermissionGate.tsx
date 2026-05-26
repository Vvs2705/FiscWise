import { ReactNode } from 'react';
import { ShieldOff } from 'lucide-react';

// Roles do sistema
export type UserRole = 'owner' | 'admin' | 'contador' | 'assistente' | 'financeiro' | 'viewer';

// Em produção, viria do contexto de autenticação.
// Por ora, simulamos o usuário como owner para fins de demo.
const CURRENT_ROLE: UserRole = 'owner';

const ROLE_HIERARCHY: Record<UserRole, number> = {
  owner: 100,
  admin: 80,
  financeiro: 60,
  contador: 50,
  assistente: 30,
  viewer: 10,
};

export function hasPermission(userRole: UserRole, requiredRole: UserRole): boolean {
  return ROLE_HIERARCHY[userRole] >= ROLE_HIERARCHY[requiredRole];
}

interface PermissionGateProps {
  requiredRole: UserRole;
  children: ReactNode;
  fallback?: ReactNode;
  silent?: boolean;
}

function AccessDenied() {
  return (
    <div className="flex flex-col items-center justify-center gap-3 rounded-xl border border-dashed border-border bg-muted/30 p-8 text-center">
      <div className="flex h-10 w-10 items-center justify-center rounded-full bg-destructive/10">
        <ShieldOff className="h-5 w-5 text-destructive" />
      </div>
      <div>
        <p className="text-sm font-medium text-foreground">Acesso não autorizado</p>
        <p className="mt-1 text-xs text-muted-foreground">
          Você não tem permissão para visualizar este conteúdo.
        </p>
      </div>
    </div>
  );
}

export function PermissionGate({ requiredRole, children, fallback, silent }: PermissionGateProps) {
  const allowed = hasPermission(CURRENT_ROLE, requiredRole);
  if (allowed) return <>{children}</>;
  if (silent) return null;
  if (fallback) return <>{fallback}</>;
  return <AccessDenied />;
}

export function useCurrentRole(): UserRole {
  return CURRENT_ROLE;
}

export function useHasPermission(requiredRole: UserRole): boolean {
  return hasPermission(CURRENT_ROLE, requiredRole);
}
