/**
 * Transporte HTTP da sincronização (contrato em OFFLINE_SYNC.md, seções 5.1, 5.3 e 5.4).
 * Os endpoints /sync/push, /sync/pull e /sync/devices/token usam o token de
 * DISPOSITIVO; /sync/devices (registro, lista, revogação) usam o token do usuário.
 */
import axios from 'axios';
import { api } from '@/lib/api';
import type { SyncEntityType, SyncOperation } from './db';

export type PullEntity = 'clients' | 'deadlines' | 'certificates' | 'receivables' | 'invoices';

export const PULL_ENTITY: Record<SyncEntityType, PullEntity> = {
  client: 'clients',
  deadline: 'deadlines',
  certificate: 'certificates',
  receivable: 'receivables',
  invoice: 'invoices',
};

export interface PushEvent {
  id: string;
  device_id: string;
  entity_type: SyncEntityType;
  entity_id: string;
  operation: SyncOperation;
  payload: Record<string, unknown>;
  base_version: number | null;
  created_at: string;
}

export interface PushAck {
  id: string;
  status: 'ack' | 'rejected';
  error?: string;
  entity?: Record<string, unknown> | null;
  conflict?: boolean;
  fields_overwritten?: Record<string, { server: unknown; client: unknown }>;
}

export interface PullCursor {
  since: string | null;
  after_id: string | null;
}

export interface PullResponse {
  rows: Array<Record<string, unknown> & { id: string }>;
  next: PullCursor;
  has_more: boolean;
}

export interface SyncTransport {
  push(events: PushEvent[]): Promise<PushAck[]>;
  pull(entity: PullEntity, cursor: PullCursor, limit: number): Promise<PullResponse>;
}

export interface DeviceRegistration {
  id: string;
  name: string;
  platform: string;
  app_version: string;
}

export interface SyncDevice {
  id: string;
  name: string;
  platform: string;
  app_version: string;
  last_seen_at: string | null;
  revoked_at: string | null;
  created_at: string;
  user_id: string;
}

export interface DeviceTokenRenewal {
  device_token: string;
  access_token: string;
  tenant_id: string;
}

export interface DeviceApi {
  register(input: DeviceRegistration): Promise<{ device: SyncDevice; device_token: string }>;
  renew(deviceToken: string): Promise<DeviceTokenRenewal>;
}

// ─── Erros tipados ───────────────────────────────────────────────────────────

/** 401 {code: 'device_revoked'}: apagar o banco local e ir para o login. */
export class DeviceRevokedError extends Error {
  constructor() {
    super('Este dispositivo foi revogado pelo escritório.');
    this.name = 'DeviceRevokedError';
  }
}

/** 401 sem revogação (token de dispositivo vencido/inválido): registrar de novo. */
export class DeviceAuthError extends Error {
  constructor(message = 'Token do dispositivo inválido ou expirado.') {
    super(message);
    this.name = 'DeviceAuthError';
  }
}

/** Sem resposta do servidor (rede caiu, DNS, timeout). */
export class SyncNetworkError extends Error {
  constructor(message = 'Sem conexão com o servidor.') {
    super(message);
    this.name = 'SyncNetworkError';
  }
}

/** 503 do push: os ACKs recebidos valem; o resto volta a pending. */
export class TransientPushError extends Error {
  acks: PushAck[];
  constructor(acks: PushAck[], message = 'Erro transitório no servidor.') {
    super(message);
    this.name = 'TransientPushError';
    this.acks = acks;
  }
}

/** Resposta HTTP de erro que não se encaixa nos casos acima (4xx/5xx). */
export class SyncHttpError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.name = 'SyncHttpError';
    this.status = status;
  }
}

export function isDeviceRevokedBody(data: unknown): boolean {
  if (!data || typeof data !== 'object') return false;
  const d = data as { code?: unknown; detail?: unknown };
  if (d.code === 'device_revoked') return true;
  if (d.detail === 'device_revoked') return true;
  if (d.detail && typeof d.detail === 'object' && (d.detail as { code?: unknown }).code === 'device_revoked') return true;
  return false;
}

function errorMessage(data: unknown, fallback: string): string {
  if (data && typeof data === 'object') {
    const d = data as { error?: unknown; detail?: unknown; message?: unknown };
    for (const v of [d.error, d.detail, d.message]) if (typeof v === 'string' && v.trim()) return v;
  }
  return fallback;
}

/** Converte erro do axios nos erros tipados da sincronização. */
export function toSyncError(error: unknown): Error {
  if (axios.isAxiosError(error)) {
    if (!error.response) return new SyncNetworkError();
    const { status, data } = error.response;
    if (status === 401) return isDeviceRevokedBody(data) ? new DeviceRevokedError() : new DeviceAuthError();
    if (status === 503 && data && typeof data === 'object' && Array.isArray((data as { acks?: unknown }).acks)) {
      return new TransientPushError((data as { acks: PushAck[] }).acks, errorMessage(data, 'Erro transitório no servidor.'));
    }
    return new SyncHttpError(status, errorMessage(data, `Erro ${status} na sincronização.`));
  }
  return error instanceof Error ? error : new Error(String(error));
}

// ─── Implementação HTTP real ─────────────────────────────────────────────────

export interface HttpTransportOptions {
  getDeviceToken: () => Promise<string | null | undefined>;
  tenantId: string;
}

export function createHttpTransport({ getDeviceToken, tenantId }: HttpTransportOptions): SyncTransport {
  async function deviceHeaders() {
    const token = await getDeviceToken();
    if (!token) throw new DeviceAuthError('Dispositivo ainda não registrado.');
    return { Authorization: `Bearer ${token}`, 'X-Tenant-ID': tenantId };
  }
  return {
    async push(events) {
      try {
        const { data } = await api.post<{ acks: PushAck[] }>(
          '/api/v1/sync/push',
          { events },
          { headers: await deviceHeaders() },
        );
        return data.acks ?? [];
      } catch (error) {
        throw toSyncError(error);
      }
    },
    async pull(entity, cursor, limit) {
      try {
        const params: Record<string, string | number> = { entity, limit };
        if (cursor.since) params.since = cursor.since;
        if (cursor.after_id) params.after_id = cursor.after_id;
        const { data } = await api.get<PullResponse>('/api/v1/sync/pull', { params, headers: await deviceHeaders() });
        return data;
      } catch (error) {
        throw toSyncError(error);
      }
    },
  };
}

export const httpDeviceApi: DeviceApi = {
  async register(input) {
    try {
      const { data } = await api.post<{ device: SyncDevice; device_token: string }>('/api/v1/sync/devices', input);
      return data;
    } catch (error) {
      throw toSyncError(error);
    }
  },
  async renew(deviceToken) {
    try {
      const { data } = await api.post<DeviceTokenRenewal>('/api/v1/sync/devices/token', null, {
        headers: { Authorization: `Bearer ${deviceToken}` },
      });
      return data;
    } catch (error) {
      throw toSyncError(error);
    }
  },
};

export async function listSyncDevices(): Promise<SyncDevice[]> {
  const { data } = await api.get<SyncDevice[] | { items?: SyncDevice[]; devices?: SyncDevice[] }>('/api/v1/sync/devices');
  if (Array.isArray(data)) return data;
  return data.items ?? data.devices ?? [];
}

export async function revokeSyncDevice(id: string): Promise<void> {
  await api.post(`/api/v1/sync/devices/${id}/revoke`);
}
