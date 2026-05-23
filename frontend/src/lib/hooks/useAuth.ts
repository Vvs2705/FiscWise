import { useAuthStore } from '@/stores/authStore';
import {
  login as authLogin,
  register as authRegister,
  loginWithGoogle as authLoginWithGoogle,
  type LoginCredentials,
  type RegisterData,
} from '@/lib/auth';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';

function getErrorMessage(error: unknown, fallback: string) {
  if (typeof error === 'object' && error !== null && 'response' in error) {
    const detail = (error as { response?: { data?: { detail?: unknown } } }).response?.data?.detail;
    return typeof detail === 'string' ? detail : fallback;
  }
  return fallback;
}

export function useAuth() {
  const { user, isAuthenticated, setUser, logout, checkAuth } = useAuthStore();
  const [isLoading, setIsLoading] = useState(false);
  const navigate = useNavigate();

  const login = async (credentials: LoginCredentials) => {
    setIsLoading(true);
    try {
      const response = await authLogin(credentials);
      setUser(response.user);
      toast.success('Login realizado com sucesso!');
      navigate('/dashboard');
    } catch (error: unknown) {
      const message = getErrorMessage(error, 'Erro ao fazer login');
      toast.error(message);
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  const register = async (data: RegisterData) => {
    setIsLoading(true);
    try {
      const response = await authRegister(data);
      setUser(response.user);
      toast.success('Conta criada com sucesso!');
      navigate('/dashboard');
    } catch (error: unknown) {
      const message = getErrorMessage(error, 'Erro ao criar conta');
      toast.error(message);
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  const loginWithGoogle = async (credential: string) => {
    setIsLoading(true);
    try {
      const response = await authLoginWithGoogle(credential);
      setUser(response.user);
      toast.success('Login realizado com sucesso!');
      navigate('/dashboard');
    } catch (error: unknown) {
      const message = getErrorMessage(error, 'Erro ao entrar com Google');
      toast.error(message);
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  return {
    user,
    isAuthenticated,
    isLoading,
    login,
    register,
    loginWithGoogle,
    logout,
    checkAuth,
  };
}
