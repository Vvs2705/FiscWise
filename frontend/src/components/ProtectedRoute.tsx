import type { ReactNode } from 'react';
import { Navigate } from 'react-router-dom';
import { useAuthStore } from '@/stores/authStore';
import { useEffect } from 'react';
import { usePermission, type UserRole } from '@/lib/hooks/usePermission';

interface ProtectedRouteProps {
  children: ReactNode;
  fallbackPath?: string;
  requiredRole?: UserRole;
  allowedRoles?: UserRole[];
}

export function ProtectedRoute({
  children,
  fallbackPath = '/dashboard',
  requiredRole,
  allowedRoles,
}: ProtectedRouteProps) {
  const { isAuthenticated, checkAuth } = useAuthStore();
  const { hasAnyRole, hasRole } = usePermission();

  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
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
