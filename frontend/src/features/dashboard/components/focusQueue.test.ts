import { describe, expect, it } from 'vitest';
import { focusQueueState } from './focusQueue';

const t = (id: string) => ({ id });

describe('focusQueueState', () => {
  it('começa na primeira tarefa', () => {
    const s = focusQueueState([t('a'), t('b'), t('c')], new Set());
    expect(s.current?.id).toBe('a');
    expect([s.position, s.total, s.finished]).toEqual([1, 3, false]);
  });

  it('não pula a próxima quando a tarefa resolvida some da lista (refetch)', () => {
    // 'a' foi resolvida e o refetch a removeu da lista
    const s = focusQueueState([t('b'), t('c')], new Set(['a']));
    expect(s.current?.id).toBe('b');
    expect([s.position, s.total]).toEqual([2, 3]);
  });

  it('avança quando a tarefa tratada continua na lista (pular/adiar)', () => {
    const s = focusQueueState([t('a'), t('b')], new Set(['a']));
    expect(s.current?.id).toBe('b');
    expect([s.position, s.total]).toEqual([2, 2]);
  });

  it('termina quando todas foram tratadas', () => {
    const s = focusQueueState([t('b')], new Set(['a', 'b']));
    expect(s.current).toBeUndefined();
    expect(s.finished).toBe(true);
    expect(s.total).toBe(2);
  });

  it('lista vazia sem nada tratado não é "concluído"', () => {
    expect(focusQueueState([], new Set()).finished).toBe(false);
  });
});
