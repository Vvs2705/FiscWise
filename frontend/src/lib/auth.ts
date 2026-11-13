import { api } from './api';
import { clearApiCache, wipeLocalDb } from './offline/db';
import { clearApiCacheIfTenantChanged } from './offline/apiCache';

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface RegisterData {
  company_name: string;
  owner_email: string;
  owner_password: string;
  owner_full_name: string;
  /** Opcional: sem ele o escritório começa com 14 dias de teste grátis do Premium. */
  plan_slug?: string;
  owner_phone?: string;
  document?: string;
  terms_accepted: boolean;
}

export interface AuthUser {
  id: string;
  email: string;
  full_name: string;
  phone?: string;
  role: string;
  /** false = escritório sem cadastro concluído (vai para /concluir-cadastro) */
  signup_complete?: boolean;
  two_factor_enabled?: boolean;
  two_factor_method?: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  tenant_id: string;
  user: AuthUser;
}

/** Returned when the server requires 2FA completion */
export interface MfaChallenge {
  status: 'requires_2fa';
  mfa_token: string;
  two_factor_method: 'totp' | 'email';
  message: string;
}

/** Primeiro acesso com Google: o e-mail não tem conta, falta o cadastro. */
export interface GoogleSignupRequired {
  status: 'requires_signup';
  signup_token: string;
  email: string;
  full_name?: string | null;
}

export type LoginResult = AuthResponse | MfaChallenge;
export type GoogleLoginResult = LoginResult | GoogleSignupRequired;

export function isMfaChallenge(r: GoogleLoginResult): r is MfaChallenge {
  return (r as MfaChallenge).status === 'requires_2fa';
}

export function isGoogleSignupRequired(r: GoogleLoginResult): r is GoogleSignupRequired {
  return (r as GoogleSignupRequired).status === 'requires_signup';
}

// O token de cadastro Google fica só nesta aba (sessionStorage) até o
// cadastro terminar; vale 30 min no servidor.
const GOOGLE_SIGNUP_KEY = 'google_signup';

export function saveGoogleSignup(data: GoogleSignupRequired): void {
  try {
    sessionStorage.setItem(GOOGLE_SIGNUP_KEY, JSON.stringify(data));
  } catch {
    // storage bloqueado: o cadastro segue em memória na própria tela
  }
}

export function getGoogleSignup(): GoogleSignupRequired | null {
  try {
    const raw = sessionStorage.getItem(GOOGLE_SIGNUP_KEY);
    const parsed = raw ? JSON.parse(raw) : null;
    return parsed && parsed.status === 'requires_signup' && parsed.signup_token ? parsed : null;
  } catch {
    return null;
  }
}

export function clearGoogleSignup(): void {
  try {
    sessionStorage.removeItem(GOOGLE_SIGNUP_KEY);
  } catch {
    // nada a limpar
  }
}

export interface GoogleRegisterData {
  signup_token: string;
  company_name: string;
  document?: string;
  owner_full_name?: string;
  owner_phone?: string;
  /** Opcional: sem ele o escritório começa com 14 dias de teste grátis do Premium. */
  plan_slug?: string;
  terms_accepted: boolean;
}

export interface CompleteSignupData {
  company_name: string;
  document?: string;
  owner_full_name?: string;
  owner_phone?: string;
  terms_accepted: boolean;
}

/**
 * Grava a sessão. Se o escritório é outro que o último neste navegador, apaga
 * antes o cache de API do service worker (navegador compartilhado).
 */
export async function storeSession({ access_token, tenant_id, user }: AuthResponse): Promise<void> {
  await clearApiCacheIfTenantChanged(tenant_id);
  localStorage.setItem('access_token', access_token);
  localStorage.setItem('tenant_id', tenant_id);
  localStorage.setItem('user', JSON.stringify(user));
}

export async function registerWithGoogle(data: GoogleRegisterData): Promise<AuthResponse> {
  const response = await api.post<AuthResponse>('/api/v1/onboarding/register-google', data);
  await storeSession(response.data);
  clearGoogleSignup();
  return response.data;
}

export async function completeSignup(data: CompleteSignupData): Promise<void> {
  await api.post('/api/v1/onboarding/complete-signup', data);
}

export interface TenantData {
  id: string;
  name: string;
  document?: string;
  plan_slug?: string;
  phone?: string;
  address?: string;
  website?: string;
  subscription_status: string;
  created_at?: string;
  /** true durante o teste grátis de 14 dias. */
  em_teste?: boolean;
  /** Fim do teste grátis (ISO), quando houver. */
  trial_ends_at?: string | null;
  /** Dias inteiros que faltam no teste (0 = acaba hoje). */
  trial_dias_restantes?: number | null;
  /** true = teste/período pago acabou sem assinatura: conta só para leitura. */
  acesso_expirado?: boolean;
}

export interface UpdateProfileData {
  full_name?: string;
  phone?: string;
}

export interface UpdateTenantData {
  name?: string;
  document?: string;
  plan_slug?: string;
  phone?: string;
  address?: string;
  website?: string;
}

export interface ChangePasswordData {
  current_password: string;
  new_password: string;
}

export interface Setup2FAResponse {
  secret: string;
  otpauth_uri: string;
  qr_code_base64: string;
  method: string;
}

export interface TwoFAStatus {
  two_factor_enabled: boolean;
  two_factor_method: 'none' | 'totp' | 'email';
}

// ─── Auth ─────────────────────────────────────────────────────────────────────

export async function login(credentials: LoginCredentials): Promise<LoginResult> {
  const params = new URLSearchParams();
  params.append('username', credentials.email);
  params.append('password', credentials.password);

  const response = await api.post<LoginResult>('/api/v1/auth/login', params, {
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
    },
  });

  const data = response.data;

  // If 2FA is required, return the challenge — do NOT store tokens yet
  if (isMfaChallenge(data)) {
    return data;
  }

  await storeSession(data as AuthResponse);

  return data;
}

export async function register(data: RegisterData): Promise<AuthResponse> {
  const response = await api.post<AuthResponse>('/api/v1/onboarding/register', data);

  await storeSession(response.data);

  return response.data;
}

/**
 * Logout explícito: apaga também o banco local offline do escritório e o cache
 * de API do service worker (computador compartilhado — OFFLINE_SYNC.md, seção 9).
 * O redirecionamento espera a limpeza (com teto de 2 s para nunca travar a saída).
 */
export function logout(redirectTo = '/'): void {
  const tenantId = localStorage.getItem('tenant_id');
  localStorage.removeItem('access_token');
  localStorage.removeItem('tenant_id');
  localStorage.removeItem('user');

  const wipe = Promise.all([tenantId ? wipeLocalDb(tenantId) : Promise.resolve(), clearApiCache()]).catch(
    () => undefined,
  );
  const timeout = new Promise((resolve) => setTimeout(resolve, 2000));
  void Promise.race([wipe, timeout]).finally(() => {
    window.location.href = redirectTo;
  });
}

export function isAuthenticated(): boolean {
  return !!localStorage.getItem('access_token');
}

export function getCurrentUser(): AuthUser | null {
  const userStr = localStorage.getItem('user');
  if (!userStr || userStr === 'undefined' || userStr === 'null') {
    localStorage.removeItem('user');
    return null;
  }
  try {
    return JSON.parse(userStr);
  } catch {
    localStorage.removeItem('user');
    return null;
  }
}

export function getTenantId(): string | null {
  return localStorage.getItem('tenant_id');
}

export async function loginWithGoogle(credential: string): Promise<GoogleLoginResult> {
  const response = await api.post<GoogleLoginResult>('/api/v1/auth/google', { credential });
  const data = response.data;

  if (isMfaChallenge(data) || isGoogleSignupRequired(data)) {
    return data;
  }

  await storeSession(data as AuthResponse);

  return data;
}

/** Complete 2FA login with mfa_token + OTP code */
export async function verify2FA(mfaToken: string, otpCode: string): Promise<AuthResponse> {
  const response = await api.post<AuthResponse>('/api/v1/auth/login/verify-2fa', {
    mfa_token: mfaToken,
    otp_code: otpCode,
  });

  await storeSession(response.data);

  return response.data;
}

// ─── 2FA Management ───────────────────────────────────────────────────────────

/** Fetch 2FA status for the authenticated user */
export async function get2FAStatus(): Promise<TwoFAStatus> {
  const { data } = await api.get<TwoFAStatus>('/api/v1/auth/2fa/status');
  return data;
}

/** Generate TOTP secret + QR code for setup */
export async function setup2FA(): Promise<Setup2FAResponse> {
  const { data } = await api.get<Setup2FAResponse>('/api/v1/auth/2fa/setup');
  return data;
}

/** Enable TOTP 2FA: confirm with first OTP code + the secret from setup */
export async function enableTOTP2FA(secret: string, otpCode: string): Promise<void> {
  await api.post('/api/v1/auth/2fa/enable-totp', { secret, otp_code: otpCode });
}

/** Initiate Email 2FA setup: sends OTP to user's email */
export async function initiateEmail2FA(): Promise<void> {
  await api.post('/api/v1/auth/2fa/enable', { method: 'email', otp_code: '000000' });
}

/** Confirm Email OTP to activate email-based 2FA */
export async function confirmEmail2FA(otpCode: string): Promise<void> {
  await api.post('/api/v1/auth/2fa/confirm-email', { otp_code: otpCode });
}

/** Disable 2FA with password confirmation */
export async function disable2FA(currentPassword: string, otpCode?: string): Promise<void> {
  await api.post('/api/v1/auth/2fa/disable', {
    current_password: currentPassword,
    otp_code: otpCode ?? null,
  });
}

// ─── Profile & Tenant ─────────────────────────────────────────────────────────

export async function fetchTenant(): Promise<TenantData> {
  const { data } = await api.get<TenantData>('/api/v1/auth/tenant');
  return data;
}

export async function updateProfile(data: UpdateProfileData): Promise<AuthUser> {
  const { data: user } = await api.patch<AuthUser>('/api/v1/auth/me', data);
  // Persist updated user to localStorage
  const stored = getCurrentUser();
  if (stored) {
    localStorage.setItem('user', JSON.stringify({ ...stored, ...user }));
  }
  return user;
}

export async function updateTenant(data: UpdateTenantData): Promise<TenantData> {
  const { data: tenant } = await api.patch<TenantData>('/api/v1/auth/tenant', data);
  return tenant;
}

export async function changePassword(data: ChangePasswordData): Promise<void> {
  // A troca de senha invalida os tokens antigos; o backend devolve um novo.
  const { data: res } = await api.post<{ access_token?: string }>('/api/v1/auth/change-password', data);
  if (res.access_token) localStorage.setItem('access_token', res.access_token);
}

// ─── Esqueci minha senha ──────────────────────────────────────────────────────

/** Mesma política do cadastro (mín. 8) + limite do bcrypt (72 bytes). */
export const NEW_PASSWORD_MIN_LENGTH = 8;
export const NEW_PASSWORD_MAX_BYTES = 72;

export function newPasswordError(password: string): string | null {
  if (password.length < NEW_PASSWORD_MIN_LENGTH) {
    return `Senha deve ter ao menos ${NEW_PASSWORD_MIN_LENGTH} caracteres`;
  }
  if (new TextEncoder().encode(password).length > NEW_PASSWORD_MAX_BYTES) {
    return 'Senha muito longa (máximo de 72 bytes)';
  }
  return null;
}

/** Sempre resolve com a mesma mensagem genérica (não revela se a conta existe). */
export async function requestPasswordReset(email: string): Promise<{ message: string }> {
  const { data } = await api.post<{ message: string }>('/api/v1/auth/password-reset/request', { email });
  return data;
}

export async function confirmPasswordReset(token: string, newPassword: string): Promise<{ message: string }> {
  const { data } = await api.post<{ message: string }>('/api/v1/auth/password-reset/confirm', {
    token,
    new_password: newPassword,
  });
  return data;
}

/** false quando a instalação não envia e-mail (recuperação indisponível). */
export async function passwordResetAvailable(): Promise<boolean> {
  const { data } = await api.get<{ available: boolean }>('/api/v1/auth/password-reset/available');
  return data.available;
}
