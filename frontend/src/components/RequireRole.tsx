import type { ReactNode } from 'react';
import { usePermission, type UserRole } from '@/lib/hooks/usePermission';

interface RequireRoleProps {
  children: ReactNode;
  fallback?: ReactNode;
  mode?: 'minimum' | 'exact';
  role?: UserRole;
  roles?: UserRole[];
}

export function RequireRole({
  children,
  fallback = null,
  mode = 'minimum',
  role,
  roles,
}: RequireRoleProps) {
  const { hasAnyRole, hasRole } = usePermission();

  const isAllowed = roles?.length
    ? hasAnyRole(roles, { mode })
    : role
      ? hasRole(role, { mode })
      : false;

  if (!isAllowed) {
    return <>{fallback}</>;
  }

  return <>{children}</>;
}
