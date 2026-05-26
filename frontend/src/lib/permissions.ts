// Funções utilitárias de permissões — exportadas separadamente para compatibilidade com react-refresh

export type UserRole = 'owner' | 'admin' | 'contador' | 'assistente' | 'financeiro' | 'viewer';

export const ROLE_HIERARCHY: Record<UserRole, number> = {
  owner: 100,
  admin: 80,
  financeiro: 60,
  contador: 50,
  assistente: 30,
  viewer: 10,
};

// Em produção, viria do contexto de autenticação.
export const CURRENT_ROLE: UserRole = 'owner';

export function hasPermission(userRole: UserRole, requiredRole: UserRole): boolean {
  return ROLE_HIERARCHY[userRole] >= ROLE_HIERARCHY[requiredRole];
}

export function useCurrentRole(): UserRole {
  return CURRENT_ROLE;
}

export function useHasPermission(requiredRole: UserRole): boolean {
  return hasPermission(CURRENT_ROLE, requiredRole);
}
