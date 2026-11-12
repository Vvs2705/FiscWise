import axios, { type InternalAxiosRequestConfig } from 'axios';

const API_URL =
  import.meta.env.VITE_API_URL ||
  (import.meta.env.DEV ? 'http://localhost:8000' : 'https://fiscwise-api-45ckqevl6a-rj.a.run.app');

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
    
    // Chamadas com token de dispositivo (/sync/push, /sync/pull, /sync/devices/token)
    // já trazem o próprio Authorization: não sobrescrever.
    if (token && !config.headers.Authorization) {
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

export const NETWORK_ERROR_MESSAGE =
  'Sem conexão com o servidor. Esta ação precisa de internet; tente novamente quando a conexão voltar.';

export function getApiErrorMessage(
  error: unknown,
  fallback = 'Ocorreu um erro inesperado.'
): string {
  if (axios.isAxiosError(error)) {
    // Sem resposta do servidor (offline/rede caiu): mensagem amigável, nunca "Network Error".
    if (!error.response && error.code !== 'ERR_CANCELED') {
      return NETWORK_ERROR_MESSAGE;
    }
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

// ─── Renovação do token de acesso pelo token de dispositivo (offline-first) ───
// A camada offline (src/lib/offline) registra aqui como renovar o token comum
// usando o token de dispositivo (POST /api/v1/sync/devices/token). Assim quem
// volta de um período offline não é expulso para o login (OFFLINE_SYNC.md 5.1.3).
type AccessTokenRenewer = () => Promise<string | null>;
let accessTokenRenewer: AccessTokenRenewer | null = null;
let renewing: Promise<string | null> | null = null;

export function setAccessTokenRenewer(fn: AccessTokenRenewer | null): void {
  accessTokenRenewer = fn;
}

async function renewAccessTokenOnce(): Promise<string | null> {
  if (!accessTokenRenewer) return null;
  if (!renewing) {
    renewing = accessTokenRenewer()
      .catch(() => null)
      .finally(() => {
        renewing = null;
      });
  }
  return renewing;
}

/** Endpoints autenticados pelo token de dispositivo: tratados pela engine de sync. */
function isDeviceTokenEndpoint(url: string | undefined): boolean {
  return !!url && /\/api\/v1\/sync\/(push|pull|devices\/token)(\?|$)/.test(url);
}

/** Login, 2FA etc.: 401 ali é credencial errada, não sessão vencida. */
function isAuthEndpoint(url: string | undefined): boolean {
  return !!url && /\/api\/v1\/auth\/(login|google|register)(\/|\?|$)/.test(url);
}

type RetriableConfig = InternalAxiosRequestConfig & { _fiscwiseRetried?: boolean };

// Response interceptor to handle 401 errors
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    // Sem resposta (rede caiu, offline): NUNCA deslogar.
    if (!axios.isAxiosError(error) || !error.response) {
      return Promise.reject(error);
    }

    const config = error.config as RetriableConfig | undefined;

    if (error.response.status === 401 && !isDeviceTokenEndpoint(config?.url)) {
      // 401 nas rotas de entrada (senha errada, código 2FA inválido, token do
      // Google recusado) é resposta normal do formulário: a tela mostra a
      // mensagem. Só sessão expirada em chamada autenticada redireciona.
      if (isAuthEndpoint(config?.url)) {
        return Promise.reject(error);
      }

      // Tenta UMA vez renovar com o token de dispositivo e repetir a requisição.
      if (config && !config._fiscwiseRetried) {
        config._fiscwiseRetried = true;
        const renewed = await renewAccessTokenOnce();
        if (renewed) {
          localStorage.setItem('access_token', renewed);
          config.headers.Authorization = `Bearer ${renewed}`;
          return api(config);
        }
      }

      let wasPortalClient = false;
      try {
        wasPortalClient = JSON.parse(localStorage.getItem('user') ?? 'null')?.role === 'client';
      } catch {
        // user corrompido no storage: trata como equipe
      }

      // Clear auth data (o banco local fica: pode haver alterações não enviadas)
      localStorage.removeItem('access_token');
      localStorage.removeItem('tenant_id');
      localStorage.removeItem('user');
      
      // Cliente do portal entra por link mágico, não pela tela da equipe
      window.location.href = wasPortalClient ? '/portal/login' : '/login';
    }
    
    return Promise.reject(error);
  }
);
