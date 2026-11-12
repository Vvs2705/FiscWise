/**
 * Fila do Modo Foco: a tarefa atual é a primeira que ainda não foi tratada.
 *
 * Usar um índice (+1 a cada ação) pulava tarefas: ao resolver uma, o refetch
 * tira o item da lista, a lista encolhe e o índice +1 cai no item seguinte ao
 * próximo. Guardando os ids tratados, a lista pode encolher (ou não) à vontade.
 */
export interface FocusQueueState<T> {
  current: T | undefined;
  /** Posição 1-based da tarefa atual. */
  position: number;
  total: number;
  finished: boolean;
}

export function focusQueueState<T extends { id: string }>(
  tasks: readonly T[],
  handled: ReadonlySet<string>,
): FocusQueueState<T> {
  const remaining = tasks.filter((t) => !handled.has(t.id));
  const done = handled.size;
  return {
    current: remaining[0],
    position: Math.min(done + 1, done + remaining.length),
    total: done + remaining.length,
    finished: done > 0 && remaining.length === 0,
  };
}
