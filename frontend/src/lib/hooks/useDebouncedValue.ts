import { useEffect, useState } from 'react';

/**
 * Devolve `value` só depois de `delay` ms sem mudanças.
 * Uso típico: o input continua controlado pelo valor imediato e o filtro da
 * lista (em `useMemo`) depende do valor "debounced", evitando refiltrar a
 * cada tecla em listas grandes.
 */
export function useDebouncedValue<T>(value: T, delay = 300): T {
  const [debounced, setDebounced] = useState(value);

  useEffect(() => {
    const id = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(id);
  }, [value, delay]);

  return debounced;
}
