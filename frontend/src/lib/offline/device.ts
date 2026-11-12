/**
 * Dispositivo de sincronização (OFFLINE_SYNC.md, seção 5.1).
 * O device_id e o token de dispositivo ficam em `sync_meta` (IndexedDB do
 * escritório), nunca no localStorage comum: são apagados junto com o banco
 * local no logout explícito ou na revogação.
 */
import { META, deleteMeta, getMeta, setMeta, type FiscWiseLocalDb } from './db';
import { DeviceAuthError, DeviceRevokedError, type DeviceApi } from './transport';

const RENEW_WINDOW_MS = 7 * 24 * 60 * 60 * 1000;
const APP_VERSION = (import.meta.env.VITE_APP_VERSION as string | undefined) ?? '1.0.0';

export async function getOrCreateDeviceId(db: FiscWiseLocalDb): Promise<string> {
  return db.transaction('rw', db.sync_meta, async () => {
    const existing = await getMeta<string>(db, META.deviceId);
    if (existing) return existing;
    const id = globalThis.crypto.randomUUID();
    await setMeta(db, META.deviceId, id);
    return id;
  });
}

export async function getDeviceToken(db: FiscWiseLocalDb): Promise<string | undefined> {
  return getMeta<string>(db, META.deviceToken);
}

/** Lê `exp` (segundos) do JWT sem verificar a assinatura. */
export function decodeJwtExp(token: string): number | null {
  try {
    const part = token.split('.')[1];
    if (!part) return null;
    const b64 = part.replace(/-/g, '+').replace(/_/g, '/');
    const padded = b64 + '='.repeat((4 - (b64.length % 4)) % 4);
    const json = JSON.parse(atob(padded)) as { exp?: unknown };
    return typeof json.exp === 'number' ? json.exp : null;
  } catch {
    return null;
  }
}

export function needsRenewal(token: string, now: Date = new Date()): boolean {
  const exp = decodeJwtExp(token);
  if (exp === null) return false;
  return exp * 1000 - now.getTime() < RENEW_WINDOW_MS;
}

export function isExpired(token: string, now: Date = new Date()): boolean {
  const exp = decodeJwtExp(token);
  return exp !== null && exp * 1000 <= now.getTime();
}

export function describeThisDevice(): { name: string; platform: string } {
  const ua = typeof navigator !== 'undefined' ? navigator.userAgent : '';
  const browser = /Edg\//.test(ua)
    ? 'Edge'
    : /OPR\//.test(ua)
      ? 'Opera'
      : /Firefox\//.test(ua)
        ? 'Firefox'
        : /Chrome\//.test(ua)
          ? 'Chrome'
          : /Safari\//.test(ua)
            ? 'Safari'
            : 'Navegador';
  let os = 'computador';
  let platform = 'web';
  if (/Android/i.test(ua)) {
    os = 'Android';
    platform = 'android';
  } else if (/iPhone|iPad|iPod/i.test(ua)) {
    os = 'iOS';
    platform = 'ios';
  } else if (/Windows/i.test(ua)) os = 'Windows';
  else if (/Mac OS X|Macintosh/i.test(ua)) os = 'macOS';
  else if (/Linux/i.test(ua)) os = 'Linux';
  const standalone =
    typeof window !== 'undefined' && typeof window.matchMedia === 'function' && window.matchMedia('(display-mode: standalone)').matches;
  return { name: `${standalone ? 'App' : browser} no ${os}`, platform };
}

export interface EnsureDeviceResult {
  deviceId: string;
  deviceToken: string | null;
  /** access_token novo devolvido pela renovação (a chamar setAccessToken) */
  accessToken?: string;
}

/**
 * Garante device_id + token de dispositivo válido: registra no primeiro login
 * online e renova quando faltar menos de 7 dias. Offline nunca lança: devolve o
 * que houver localmente. Revogação é propagada (DeviceRevokedError).
 */
export async function ensureDevice(
  db: FiscWiseLocalDb,
  deviceApi: DeviceApi,
  opts: { now?: Date; hasUserSession?: boolean } = {},
): Promise<EnsureDeviceResult> {
  const now = opts.now ?? new Date();
  const deviceId = await getOrCreateDeviceId(db);
  let token = await getDeviceToken(db);

  if (token && isExpired(token, now)) {
    await deleteMeta(db, META.deviceToken);
    token = undefined;
  }

  try {
    if (!token) {
      if (opts.hasUserSession === false) return { deviceId, deviceToken: null };
      const { name, platform } = describeThisDevice();
      const res = await deviceApi.register({ id: deviceId, name, platform, app_version: APP_VERSION });
      await setMeta(db, META.deviceToken, res.device_token);
      return { deviceId, deviceToken: res.device_token };
    }
    if (needsRenewal(token, now)) {
      const res = await deviceApi.renew(token);
      await setMeta(db, META.deviceToken, res.device_token);
      return { deviceId, deviceToken: res.device_token, accessToken: res.access_token };
    }
  } catch (error) {
    if (error instanceof DeviceRevokedError) throw error;
    if (error instanceof DeviceAuthError && token) {
      // token de dispositivo recusado: descarta para registrar de novo no próximo ciclo
      await deleteMeta(db, META.deviceToken);
      return { deviceId, deviceToken: null };
    }
    // sem rede ou falha do servidor: segue com o que houver localmente
  }
  return { deviceId, deviceToken: token ?? null };
}

/**
 * Renova o token de acesso comum usando o token de dispositivo
 * (chamado pelo interceptor de 401 antes de deslogar).
 */
export async function renewAccessTokenWithDevice(db: FiscWiseLocalDb, deviceApi: DeviceApi): Promise<string | null> {
  const token = await getDeviceToken(db);
  if (!token || isExpired(token)) return null;
  const res = await deviceApi.renew(token);
  await setMeta(db, META.deviceToken, res.device_token);
  return res.access_token;
}
