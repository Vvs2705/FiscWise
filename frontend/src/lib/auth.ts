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
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  tenant_id: string;
  user: {
    id: string;
    email: string;
    full_name: string;
    role: string;
  };
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

  // Store auth data
  localStorage.setItem('access_token', access_token);
  localStorage.setItem('tenant_id', tenant_id);
  localStorage.setItem('user', JSON.stringify(user));

  return response.data;
}

export async function register(data: RegisterData): Promise<AuthResponse> {
  const response = await api.post<AuthResponse>('/api/v1/onboarding/register', data);

  const { access_token, tenant_id, user } = response.data;

  // Store auth data
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

export function getCurrentUser() {
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
