// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { createElement, type ReactNode } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { act, renderHook, waitFor } from '@testing-library/react';
import { AxiosError, type AxiosResponse } from 'axios';
import { api } from '@/lib/api';
import { useAuthStore } from '@/stores/authStore';
import { META, openLocalDb, setMeta, wipeLocalDb, type LocalClient } from '@/lib/offline/db';
import { useClients, useCreateClient, useDeleteClient, type AccountingClient } from './useOperations';

let tenantCounter = 0;
let tenantId = '';

function wrapper() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return ({ children }: { children: ReactNode }) => createElement(QueryClientProvider, { client }, children);
}

function login(role: string) {
  tenantCounter += 1;
  tenantId = `tenant-hooks-${tenantCounter}-${Math.random().toString(36).slice(2)}`;
  localStorage.setItem('tenant_id', tenantId);
  useAuthStore.setState({
    isAuthenticated: true,
    user: { id: 'u-1', email: 'u@x.com', full_name: 'U', role, tenant_id: tenantId } as never,
  });
}

function ok<T>(data: T): AxiosResponse<T> {
  return { data, status: 200, statusText: 'OK', headers: {}, config: {} as never };
}

function serverClient(id: string, name: string): AccountingClient {
  const ts = '2026-01-01T00:00:00.000Z';
  return { id, tenant_id: tenantId, client_code: id, name, entity_type: 'pj', status: 'active', created_at: ts, updated_at: ts };
}

function localClient(id: string, name: string, extra: Partial<LocalClient> = {}): LocalClient {
  return { ...serverClient(id, name), version: 1, _sync_status: 'synced', _sync_error: null, ...extra };
}

beforeEach(() => {
  vi.restoreAllMocks();
});

afterEach(async () => {
  if (tenantId) await wipeLocalDb(tenantId).catch(() => undefined);
  localStorage.clear();
});

describe('useClients local-first', () => {
  it('com banco local e carga inicial feita, lê do Dexie (ordem por nome) sem chamar a API', async () => {
    login('admin');
    const db = openLocalDb(tenantId);
    await db.clients.bulkPut([
      localClient('c-2', 'Zeta Ltda'),
      localClient('c-1', 'Álamo Comércio', { _sync_status: 'pending' }),
      localClient('c-3', 'Beta ME'),
    ]);
    await setMeta(db, META.cursor('client'), { since: '2026-01-01T00:00:00.000Z', after_id: 'c-3' });
    const get = vi.spyOn(api, 'get');

    const { result } = renderHook(() => useClients(), { wrapper: wrapper() });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(get).not.toHaveBeenCalled();
    expect(result.current.data?.map((c) => c.name)).toEqual(['Álamo Comércio', 'Beta ME', 'Zeta Ltda']);
    expect(result.current.data?.[0]._sync_status).toBe('pending');
  });

  it('antes da carga inicial busca na API e semeia o banco como synced', async () => {
    login('admin');
    const db = openLocalDb(tenantId);
    const get = vi.spyOn(api, 'get').mockResolvedValue(ok([serverClient('s-1', 'Servidor SA')]));

    const { result } = renderHook(() => useClients(), { wrapper: wrapper() });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(get).toHaveBeenCalledWith('/api/v1/clients');
    expect(result.current.data?.map((c) => c.name)).toEqual(['Servidor SA']);
    expect((await db.clients.get('s-1'))?._sync_status).toBe('synced');
  });

  it('antes da carga inicial e sem rede, devolve o que há no banco local', async () => {
    login('admin');
    const db = openLocalDb(tenantId);
    await db.clients.put(localClient('c-9', 'Offline Ltda', { _sync_status: 'pending' }));
    vi.spyOn(api, 'get').mockRejectedValue(new AxiosError('Network Error', 'ERR_NETWORK'));

    const { result } = renderHook(() => useClients(), { wrapper: wrapper() });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.map((c) => c.id)).toEqual(['c-9']);
  });
});

describe('mutations local-first', () => {
  it('criar cliente grava a linha pending e o evento create na outbox, sem chamar a API', async () => {
    login('admin');
    const db = openLocalDb(tenantId);
    const post = vi.spyOn(api, 'post');

    const { result } = renderHook(() => useCreateClient(), { wrapper: wrapper() });
    let created: AccountingClient | undefined;
    await act(async () => {
      created = await result.current.mutateAsync({ name: 'Padaria Sol', entity_type: 'pj', status: 'active' });
    });

    expect(post).not.toHaveBeenCalled();
    const row = await db.clients.get(created!.id);
    expect(row?.name).toBe('Padaria Sol');
    expect(row?._sync_status).toBe('pending');
    const events = await db.sync_outbox.toArray();
    expect(events).toHaveLength(1);
    expect(events[0]).toMatchObject({ entity_type: 'client', entity_id: created!.id, operation: 'create', status: 'pending' });
  });

  it('excluir cliente desativa localmente (status inactive) e enfileira delete', async () => {
    login('admin');
    const db = openLocalDb(tenantId);
    await db.clients.put(localClient('c-1', 'Cliente Um'));
    const del = vi.spyOn(api, 'delete');

    const { result } = renderHook(() => useDeleteClient(), { wrapper: wrapper() });
    await act(async () => {
      await result.current.mutateAsync('c-1');
    });

    expect(del).not.toHaveBeenCalled();
    expect((await db.clients.get('c-1'))?.status).toBe('inactive');
    expect((await db.sync_outbox.toArray())[0]).toMatchObject({ operation: 'delete', entity_id: 'c-1' });
  });
});

describe('sem banco local (portal, role client)', () => {
  it('lista e cria pela API', async () => {
    login('client');
    const get = vi.spyOn(api, 'get').mockResolvedValue(ok([serverClient('p-1', 'Minha Empresa')]));
    const post = vi.spyOn(api, 'post').mockResolvedValue(ok(serverClient('p-2', 'Nova')));

    const list = renderHook(() => useClients(), { wrapper: wrapper() });
    await waitFor(() => expect(list.result.current.isSuccess).toBe(true));
    expect(get).toHaveBeenCalledWith('/api/v1/clients');
    expect(list.result.current.data?.map((c) => c.name)).toEqual(['Minha Empresa']);

    const create = renderHook(() => useCreateClient(), { wrapper: wrapper() });
    await act(async () => {
      await create.result.current.mutateAsync({ name: 'Nova', entity_type: 'pj', status: 'active' });
    });
    expect(post).toHaveBeenCalledWith('/api/v1/clients', { name: 'Nova', entity_type: 'pj', status: 'active' });
  });
});
