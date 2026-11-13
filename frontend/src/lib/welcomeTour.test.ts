// @vitest-environment jsdom
import { beforeEach, describe, expect, it, vi } from 'vitest';

const get = vi.fn();
const post = vi.fn();
const drive = vi.fn();
vi.mock('@/lib/api', () => ({ api: { get: (...a: unknown[]) => get(...a), post: (...a: unknown[]) => post(...a) } }));
vi.mock('@/lib/auth', () => ({ getCurrentUser: () => ({ id: 'u1', full_name: 'Ana Ribeiro' }) }));
vi.mock('@/lib/tours', () => ({
  loadDriver: async () => (opts: { onDestroyed: () => void }) => ({
    drive: () => {
      drive();
      opts.onDestroyed();
    },
  }),
}));

import { hasSeenWelcomeTour, maybeStartWelcomeTour } from './welcomeTour';

describe('tour de boas-vindas', () => {
  beforeEach(() => {
    localStorage.clear();
    get.mockReset();
    post.mockReset().mockResolvedValue({ data: {} });
    drive.mockReset();
  });

  it('aparece no primeiro acesso e fica marcado na conta', async () => {
    get.mockResolvedValue({ data: { welcome_tour_seen: false } });
    await maybeStartWelcomeTour();
    expect(drive).toHaveBeenCalledTimes(1);
    expect(post).toHaveBeenCalledWith('/api/v1/auth/me/welcome-tour');
    expect(hasSeenWelcomeTour()).toBe(true);

    await maybeStartWelcomeTour();
    expect(drive).toHaveBeenCalledTimes(1);
  });

  it('não aparece se a conta já viu, mesmo em outro aparelho', async () => {
    get.mockResolvedValue({ data: { welcome_tour_seen: true } });
    await maybeStartWelcomeTour();
    expect(drive).not.toHaveBeenCalled();
    expect(hasSeenWelcomeTour()).toBe(true);
  });

  it('na dúvida (sem conexão), não aparece', async () => {
    get.mockRejectedValue(new Error('offline'));
    await maybeStartWelcomeTour();
    expect(drive).not.toHaveBeenCalled();
  });
});
