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
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  tenant_id: string;
  user: AuthUser;
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

export async function login(credentials: LoginCredentials): Promise<AuthResponse> {
  const params = new URLSearchParams();
  params.append('username', credentials.email);
  params.append('password', credentials.password);

  const response = await api.post<AuthResponse>('/api/v1/auth/login', params, {
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
    },
  });

  const { access_token, tenant_id, user } = response.data;

  localStorage.setItem('access_token', access_token);
  localStorage.setItem('tenant_id', tenant_id);
  localStorage.setItem('user', JSON.stringify(user));

  return response.data;
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

export async function loginWithGoogle(credential: string): Promise<AuthResponse> {
  const response = await api.post<AuthResponse>('/api/v1/auth/google', { credential });

  const { access_token, tenant_id, user } = response.data;

  localStorage.setItem('access_token', access_token);
  localStorage.setItem('tenant_id', tenant_id);
  localStorage.setItem('user', JSON.stringify(user));

  return response.data;
}

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
