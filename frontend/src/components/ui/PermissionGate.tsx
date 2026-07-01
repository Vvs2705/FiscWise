import { ReactNode } from 'react';
import { ShieldOff } from 'lucide-react';
import { usePermission, type UserRole } from '@/lib/hooks/usePermission';

interface PermissionGateProps {
  /**
   * Minimum role required to view the gated content. The check is inclusive
   * (hierarchy-based): a user whose role ranks at or above `requiredRole`
   * passes. Roles come from the authenticated user in the auth store.
   */
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
  const { hasRole } = usePermission();
  // Fail-closed: hasRole returns false when the user is unauthenticated or has
  // no recognized role, so unknown/absent roles are denied by default.
  const allowed = hasRole(requiredRole);
  if (allowed) return <>{children}</>;
  if (silent) return null;
  if (fallback) return <>{fallback}</>;
  return <AccessDenied />;
}
