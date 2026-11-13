import axios, { type InternalAxiosRequestConfig } from 'axios';
import { API_URL } from './apiUrl';
import { clearApiCache } from './offline/apiCache';
import { toast } from 'sonner';

/** Conta só para leitura (teste grátis ou período pago acabou sem assinatura). */
export const ACESSO_EXPIRADO_CODE = 'ACESSO_EXPIRADO';
/** Evento de janela disparado a cada 402 ACESSO_EXPIRADO (a faixa do layout se atualiza). */
export const ACESSO_EXPIRADO_EVENT = 'fiscwise:acesso-expirado';
const ACESSO_EXPIRADO_FALLBACK =
  'Seu teste grátis acabou. Assine um plano para voltar a cadastrar e editar. ' +
  'Seus dados continuam disponíveis para consulta e exportação.';

export function isAcessoExpiradoError(error: unknown): boolean {
  return (
    axios.isAxiosError(error) &&
    error.response?.status === 402 &&
    String(error.response.headers?.['x-error-code'] ?? '') === ACESSO_EXPIRADO_CODE
  );
}

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

    // Conta só para leitura: avisa com o caminho para assinar, sem deslogar.
    // O id fixo junta vários 402 seguidos num aviso só.
    if (isAcessoExpiradoError(error)) {
      const detail = (error.response.data as { detail?: unknown } | undefined)?.detail;
      toast.error(typeof detail === 'string' && detail.trim() ? detail : ACESSO_EXPIRADO_FALLBACK, {
        id: ACESSO_EXPIRADO_CODE,
        duration: 10_000,
        action: { label: 'Assinar', onClick: () => window.location.assign('/assinatura') },
      });
      window.dispatchEvent(new Event(ACESSO_EXPIRADO_EVENT));
      return Promise.reject(error);
    }

    // Escritório sem cadastro concluído: o servidor recusa o sistema todo.
    if (
      error.response.status === 403 &&
      String(error.response.headers?.['x-error-code'] ?? '') === 'SIGNUP_INCOMPLETE'
    ) {
      try {
        const stored = JSON.parse(localStorage.getItem('user') ?? 'null');
        if (stored) localStorage.setItem('user', JSON.stringify({ ...stored, signup_complete: false }));
      } catch {
        // user corrompido: a página de cadastro confere pelo /auth/me
      }
      if (window.location.pathname !== '/concluir-cadastro') {
        window.location.href = '/concluir-cadastro';
      }
      return Promise.reject(error);
    }

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

      // Clear auth data (o banco local fica: pode haver alterações não enviadas).
      // O cache HTTP do service worker sai junto: é chaveado só pela URL e não
      // pode servir dados deste escritório para quem entrar depois.
      localStorage.removeItem('access_token');
      localStorage.removeItem('tenant_id');
      localStorage.removeItem('user');

      // Cliente do portal entra por link mágico, não pela tela da equipe
      const target = wasPortalClient ? '/portal/login' : '/login';
      const timeout = new Promise((resolve) => setTimeout(resolve, 1500));
      await Promise.race([clearApiCache(), timeout]);
      window.location.href = target;
    }
    
    return Promise.reject(error);
  }
);
