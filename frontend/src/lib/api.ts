import axios from 'axios';

const API_URL =
  import.meta.env.VITE_API_URL ||
  (import.meta.env.DEV ? 'http://localhost:8000' : 'https://api.fiscwise.com.br');

export const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token and tenant ID
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    const tenantId = localStorage.getItem('tenant_id');
    
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    
    if (tenantId) {
      config.headers['X-Tenant-ID'] = tenantId;
    }
    
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

export function getApiErrorMessage(
  error: unknown,
  fallback = 'Ocorreu um erro inesperado.'
): string {
  if (axios.isAxiosError(error)) {
    const responseData = error.response?.data;
    if (
      responseData &&
      typeof responseData === 'object' &&
      'detail' in responseData &&
      typeof responseData.detail === 'string' &&
      responseData.detail.trim()
    ) {
      return responseData.detail;
    }

    if (
      responseData &&
      typeof responseData === 'object' &&
      'message' in responseData &&
      typeof responseData.message === 'string' &&
      responseData.message.trim()
    ) {
      return responseData.message;
    }

    if (typeof error.message === 'string' && error.message.trim()) {
      return error.message;
    }
  }

  if (error instanceof Error && error.message.trim()) {
    return error.message;
  }

  return fallback;
}

// Response interceptor to handle 401 errors
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      let wasPortalClient = false;
      try {
        wasPortalClient = JSON.parse(localStorage.getItem('user') ?? 'null')?.role === 'client';
      } catch {
        // user corrompido no storage: trata como equipe
      }

      // Clear auth data
      localStorage.removeItem('access_token');
      localStorage.removeItem('tenant_id');
      localStorage.removeItem('user');
      
      // Cliente do portal entra por link mágico, não pela tela da equipe
      window.location.href = wasPortalClient ? '/portal/login' : '/login';
    }
    
    return Promise.reject(error);
  }
);
