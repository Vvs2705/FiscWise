import { create } from 'zustand';
import { getCurrentUser, isAuthenticated, logout as authLogout } from '@/lib/auth';

interface User {
  id: string;
  email: string;
  full_name: string;
  role: string;
}

interface AuthStore {
  user: User | null;
  isAuthenticated: boolean;
  setUser: (user: User | null) => void;
  logout: () => void;
  checkAuth: () => void;
}

export const useAuthStore = create<AuthStore>((set) => ({
  user: getCurrentUser(),
  isAuthenticated: isAuthenticated(),
  
  setUser: (user) => set({ user, isAuthenticated: !!user }),
  
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
