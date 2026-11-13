import type { ReactNode } from 'react';
import { Navigate } from 'react-router-dom';
import { useAuthStore } from '@/stores/authStore';
import { useEffect } from 'react';
import { api } from '@/lib/api';
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
  const { isAuthenticated, checkAuth, user, updateUser } = useAuthStore();
  const { hasAnyRole, hasRole } = usePermission();

  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  // Escritório sem cadastro concluído não entra no sistema (o servidor também
  // recusa com 403 SIGNUP_INCOMPLETE). Confere uma vez por sessão.
  const needsSignupCheck =
    area === 'office' && isAuthenticated && !!user && user.role !== 'client' && user.signup_complete === undefined;
  useEffect(() => {
    if (!needsSignupCheck) return;
    void api
      .get<{ signup_complete?: boolean }>('/api/v1/auth/me')
      .then(({ data }) => updateUser({ signup_complete: data.signup_complete !== false }))
      .catch(() => undefined); // offline: segue; o servidor bloqueia na volta
  }, [needsSignupCheck, updateUser]);

  const redirect = areaRedirect(area, isAuthenticated, user?.role);
  if (redirect) {
    return <Navigate to={redirect} replace />;
  }

  if (area === 'office' && isAuthenticated && user?.signup_complete === false) {
    return <Navigate to="/concluir-cadastro" replace />;
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
