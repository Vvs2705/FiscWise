import type { ReactNode } from 'react';
import { Navigate } from 'react-router-dom';
import { useAuthStore } from '@/stores/authStore';
import { useEffect } from 'react';
import { usePermission, type UserRole } from '@/lib/hooks/usePermission';
import { areaRedirect, type AppArea } from '@/features/portal/access';

interface ProtectedRouteProps {
  children: ReactNode;
  fallbackPath?: string;
  requiredRole?: UserRole;
  allowedRoles?: UserRole[];
  /** Área do app: escritório (padrão) ou portal do cliente final. */
  area?: AppArea;
}

export function ProtectedRoute({
  children,
  fallbackPath = '/dashboard',
  requiredRole,
  allowedRoles,
  area = 'office',
}: ProtectedRouteProps) {
  const { isAuthenticated, checkAuth, user } = useAuthStore();
  const { hasAnyRole, hasRole } = usePermission();

  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  const redirect = areaRedirect(area, isAuthenticated, user?.role);
  if (redirect) {
    return <Navigate to={redirect} replace />;
  }

  const isAuthorized = allowedRoles?.length
    ? hasAnyRole(allowedRoles, { mode: 'exact' })
    : requiredRole
      ? hasRole(requiredRole)
      : true;

  if (!isAuthorized) {
    return <Navigate to={fallbackPath} replace />;
  }

  return <>{children}</>;
}
