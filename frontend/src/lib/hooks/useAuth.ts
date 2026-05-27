import { useAuthStore } from '@/stores/authStore';
import {
  login as authLogin,
  register as authRegister,
  loginWithGoogle as authLoginWithGoogle,
  verify2FA as authVerify2FA,
  isMfaChallenge,
  type LoginCredentials,
  type RegisterData,
  type MfaChallenge,
} from '@/lib/auth';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';

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
  /**
   * When the server requires 2FA, we store the challenge here so the
   * LoginPage can render the OTP input screen.
   */
  const [mfaChallenge, setMfaChallenge] = useState<MfaChallenge | null>(null);
  const navigate = useNavigate();

  const login = async (credentials: LoginCredentials) => {
    setIsLoading(true);
    try {
      const result = await authLogin(credentials);
      if (isMfaChallenge(result)) {
        // Signal the UI to show the 2FA OTP screen
        setMfaChallenge(result);
        toast(result.message, { icon: '🔐' });
        return; // Do NOT navigate yet
      }
      setUser(result.user);
      setMfaChallenge(null);
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
      const result = await authLoginWithGoogle(credential);
      if (isMfaChallenge(result)) {
        setMfaChallenge(result);
        toast(result.message, { icon: '🔐' });
        return;
      }
      setUser(result.user);
      setMfaChallenge(null);
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

  /** Called after the user enters the OTP code on the 2FA screen */
  const verify2FA = async (otpCode: string) => {
    if (!mfaChallenge) return;
    setIsLoading(true);
    try {
      const response = await authVerify2FA(mfaChallenge.mfa_token, otpCode);
      setUser(response.user);
      setMfaChallenge(null);
      toast.success('Login realizado com sucesso!');
      navigate('/dashboard');
    } catch (error: unknown) {
      const message = getErrorMessage(error, 'Código inválido. Tente novamente.');
      toast.error(message);
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  /** Cancel the 2FA challenge and go back to the login form */
  const cancelMfa = () => setMfaChallenge(null);

  return {
    user,
    isAuthenticated,
    isLoading,
    mfaChallenge,
    login,
    register,
    loginWithGoogle,
    verify2FA,
    cancelMfa,
    logout,
    checkAuth,
  };
}
