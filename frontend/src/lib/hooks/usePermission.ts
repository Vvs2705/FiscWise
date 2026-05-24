import { useCallback, useMemo } from 'react';
import { useAuthStore } from '@/stores/authStore';

export const USER_ROLES = ['client', 'member', 'admin', 'owner'] as const;

export type UserRole = (typeof USER_ROLES)[number];

type PermissionMode = 'minimum' | 'exact';

interface PermissionOptions {
  mode?: PermissionMode;
}

interface PermissionState {
  isAuthenticated: boolean;
  userRole: UserRole | null;
  hasRole: (role: UserRole, options?: PermissionOptions) => boolean;
  hasAnyRole: (roles: UserRole[], options?: PermissionOptions) => boolean;
}

const roleRank: Record<UserRole, number> = {
  client: 0,
  member: 1,
  admin: 2,
  owner: 3,
};

function isUserRole(role: string | undefined): role is UserRole {
  return USER_ROLES.some((knownRole) => knownRole === role);
}

function canAccessRole(userRole: UserRole | null, requiredRole: UserRole, mode: PermissionMode) {
  if (!userRole) return false;
  if (mode === 'exact') return userRole === requiredRole;
  return roleRank[userRole] >= roleRank[requiredRole];
}

export function usePermission(): PermissionState {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  const rawRole = useAuthStore((state) => state.user?.role);

  const userRole = useMemo(() => {
    return isUserRole(rawRole) ? rawRole : null;
  }, [rawRole]);

  const hasRole = useCallback(
    (role: UserRole, options: PermissionOptions = {}) => {
      return isAuthenticated && canAccessRole(userRole, role, options.mode ?? 'minimum');
    },
    [isAuthenticated, userRole],
  );

  const hasAnyRole = useCallback(
    (roles: UserRole[], options: PermissionOptions = {}) => {
      return roles.some((role) => hasRole(role, options));
    },
    [hasRole],
  );

  return {
    isAuthenticated,
    userRole,
    hasRole,
    hasAnyRole,
  };
}
