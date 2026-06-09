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
import axios from 'axios';
import { getApiErrorMessage } from '@/lib/api';

/**
 * Resolve a user-friendly auth error message while distinguishing failure
 * classes so the user gets actionable feedback instead of a silent dead-end
 * (see CORRECOES.md C2):
 *   - network / CORS failure (no HTTP response reached the browser)
 *   - 5xx server error
 *   - 401 invalid credentials
 *   - other API errors (uses the `detail` returned by the backend)
 *
 * The real error is always logged so it shows up in the browser console and
 * any monitoring (Sentry) for diagnosis.
 */
function getAuthErrorMessage(error: unknown, fallback: string): string {
  // Always log the underlying error for diagnostics.
  console.error('[auth] login failed:', error);

  if (axios.isAxiosError(error)) {
    // No response → request never completed (network down, CORS, DNS, timeout).
    if (!error.response) {
      return 'Não foi possível entrar. Verifique sua conexão e tente novamente.';
    }

    const status = error.response.status;

    if (status === 401) {
      // Prefer the backend message when present, fall back to a clear default.
      return getApiErrorMessage(error, 'E-mail ou senha incorretos.');
    }

    if (status >= 500) {
      return 'Nossos servidores estão instáveis no momento. Tente novamente em instantes.';
    }

    return getApiErrorMessage(error, fallback);
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
      const message = getAuthErrorMessage(error, 'Erro ao fazer login');
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
      const message = getAuthErrorMessage(error, 'Erro ao criar conta');
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
      const message = getAuthErrorMessage(error, 'Erro ao entrar com Google');
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
      const message = getAuthErrorMessage(error, 'Código inválido. Tente novamente.');
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
