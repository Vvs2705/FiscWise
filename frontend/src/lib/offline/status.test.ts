import { describe, expect, it } from 'vitest';
import { formatSyncIndicator, isEffectivelyOffline, syncIndicatorTone } from './status';
import { decodeJwtExp, ensureDevice, needsRenewal } from './device';
import { FiscWiseLocalDb, META, getMeta } from './db';
import { DeviceRevokedError, type DeviceApi } from './transport';

const base = { online: true, phase: 'idle' as const, pending: 0, errors: 0, batchTotal: 0, batchDone: 0 };

describe('formatSyncIndicator', () => {
  it('Online só quando o último push/pull respondeu', () => {
    expect(formatSyncIndicator(base)).toBe('Online');
    expect(syncIndicatorTone(base)).toBe('online');
  });
  it('Offline (N pendentes)', () => {
    expect(formatSyncIndicator({ ...base, online: false, pending: 3 })).toBe('Offline (3 pendentes)');
    expect(formatSyncIndicator({ ...base, online: false, pending: 1 })).toBe('Offline (1 pendente)');
  });
  it('Sincronizando (x de y)', () => {
    expect(formatSyncIndicator({ ...base, phase: 'pushing', batchTotal: 500, batchDone: 200 })).toBe('Sincronizando (200 de 500)');
  });
  it('Erro (N itens) tem prioridade', () => {
    expect(formatSyncIndicator({ ...base, errors: 2, phase: 'pushing' })).toBe('Erro (2 itens)');
    expect(formatSyncIndicator({ ...base, errors: 1 })).toBe('Erro (1 item)');
  });
  it('sem internet efetiva', () => {
    expect(isEffectivelyOffline({ networkUp: false, online: true, lastErrorKind: null })).toBe(true);
    expect(isEffectivelyOffline({ networkUp: true, online: false, lastErrorKind: 'network' })).toBe(true);
    expect(isEffectivelyOffline({ networkUp: true, online: false, lastErrorKind: 'server' })).toBe(false);
  });
});

function jwt(expSeconds: number): string {
  const b = (o: object) => btoa(JSON.stringify(o)).replace(/=+$/, '').replace(/\+/g, '-').replace(/\//g, '_');
  return `${b({ alg: 'HS256' })}.${b({ exp: expSeconds, typ: 'device' })}.sig`;
}

describe('dispositivo', () => {
  const now = new Date('2026-11-12T12:00:00Z');
  const in30d = Math.floor(now.getTime() / 1000) + 30 * 86400;
  const in3d = Math.floor(now.getTime() / 1000) + 3 * 86400;

  it('decodifica exp sem verificar e renova com menos de 7 dias', () => {
    expect(decodeJwtExp(jwt(in30d))).toBe(in30d);
    expect(decodeJwtExp('lixo')).toBeNull();
    expect(needsRenewal(jwt(in30d), now)).toBe(false);
    expect(needsRenewal(jwt(in3d), now)).toBe(true);
  });

  it('registra no primeiro login, guarda o token no sync_meta e renova perto do vencimento', async () => {
    const db = new FiscWiseLocalDb('t-dev', `fiscwise-dev-${Math.random()}`);
    const calls: string[] = [];
    const api: DeviceApi = {
      async register(input) {
        calls.push(`register:${input.id}`);
        return { device: { ...input, last_seen_at: null, revoked_at: null, created_at: '', user_id: 'u' }, device_token: jwt(in3d) };
      },
      async renew() {
        calls.push('renew');
        return { device_token: jwt(in30d), access_token: 'novo-access', tenant_id: 't-dev' };
      },
    };
    const first = await ensureDevice(db, api, { now });
    expect(calls[0]).toBe(`register:${first.deviceId}`);
    expect(await getMeta(db, META.deviceToken)).toBe(jwt(in3d));
    const second = await ensureDevice(db, api, { now });
    expect(second.accessToken).toBe('novo-access');
    expect(await getMeta(db, META.deviceToken)).toBe(jwt(in30d));
    expect(calls).toEqual([`register:${first.deviceId}`, 'renew']);
    expect(second.deviceId).toBe(first.deviceId);
  });

  it('revogação propaga', async () => {
    const db = new FiscWiseLocalDb('t-dev2', `fiscwise-dev2-${Math.random()}`);
    const api: DeviceApi = {
      register: async () => {
        throw new DeviceRevokedError();
      },
      renew: async () => {
        throw new DeviceRevokedError();
      },
    };
    await expect(ensureDevice(db, api, { now })).rejects.toBeInstanceOf(DeviceRevokedError);
  });
});
