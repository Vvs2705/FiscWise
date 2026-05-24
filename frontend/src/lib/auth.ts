import { api } from './api';

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface RegisterData {
  company_name: string;
  owner_email: string;
  owner_password: string;
  owner_full_name: string;
  plan_slug: string;
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

export type LoginResult = AuthResponse | MfaChallenge;

export function isMfaChallenge(r: LoginResult): r is MfaChallenge {
  return (r as MfaChallenge).status === 'requires_2fa';
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

  const { access_token, tenant_id, user } = data as AuthResponse;
  localStorage.setItem('access_token', access_token);
  localStorage.setItem('tenant_id', tenant_id);
  localStorage.setItem('user', JSON.stringify(user));

  return data;
}

export async function register(data: RegisterData): Promise<AuthResponse> {
  const response = await api.post<AuthResponse>('/api/v1/onboarding/register', data);

  const { access_token, tenant_id, user } = response.data;

  localStorage.setItem('access_token', access_token);
  localStorage.setItem('tenant_id', tenant_id);
  localStorage.setItem('user', JSON.stringify(user));

  return response.data;
}

export function logout(): void {
  localStorage.removeItem('access_token');
  localStorage.removeItem('tenant_id');
  localStorage.removeItem('user');
  window.location.href = '/login';
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

export async function loginWithGoogle(credential: string): Promise<LoginResult> {
  const response = await api.post<LoginResult>('/api/v1/auth/google', { credential });
  const data = response.data;

  if (isMfaChallenge(data)) {
    return data;
  }

  const { access_token, tenant_id, user } = data as AuthResponse;
  localStorage.setItem('access_token', access_token);
  localStorage.setItem('tenant_id', tenant_id);
  localStorage.setItem('user', JSON.stringify(user));

  return data;
}

/** Complete 2FA login with mfa_token + OTP code */
export async function verify2FA(mfaToken: string, otpCode: string): Promise<AuthResponse> {
  const response = await api.post<AuthResponse>('/api/v1/auth/login/verify-2fa', {
    mfa_token: mfaToken,
    otp_code: otpCode,
  });

  const { access_token, tenant_id, user } = response.data;
  localStorage.setItem('access_token', access_token);
  localStorage.setItem('tenant_id', tenant_id);
  localStorage.setItem('user', JSON.stringify(user));

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
  await api.post('/api/v1/auth/change-password', data);
}
