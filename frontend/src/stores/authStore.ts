import { create } from 'zustand';
import { getCurrentUser, isAuthenticated, logout as authLogout } from '@/lib/auth';
import type { AuthUser } from '@/lib/auth';

interface AuthStore {
  user: AuthUser | null;
  isAuthenticated: boolean;
  setUser: (user: AuthUser | null) => void;
  updateUser: (partial: Partial<AuthUser>) => void;
  logout: () => void;
  checkAuth: () => void;
}

export const useAuthStore = create<AuthStore>((set, get) => ({
  user: getCurrentUser(),
  isAuthenticated: isAuthenticated(),

  setUser: (user) => set({ user, isAuthenticated: !!user }),

  updateUser: (partial) => {
    const current = get().user;
    if (!current) return;
    const updated = { ...current, ...partial };
    set({ user: updated });
    localStorage.setItem('user', JSON.stringify(updated));
  },

  logout: () => {
    authLogout();
    set({ user: null, isAuthenticated: false });
  },

  checkAuth: () => {
    const user = getCurrentUser();
    const authenticated = isAuthenticated();
    set({ user, isAuthenticated: authenticated });
  },
}));
