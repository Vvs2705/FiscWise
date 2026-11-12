"""Cache em memória com TTL, assíncrono, para dados globais muito lidos e pouco
alterados (catálogo de planos, regras de obrigação).

Sem Redis de propósito (custo zero, Cloud Run com no máximo 1 instância). Cada
instância tem o próprio cache; o TTL curto (5 min) limita a defasagem e
`invalidate()` limpa na hora quando a própria API altera a tabela.

NUNCA guarde aqui dado de tenant. Guarde só valores imutáveis/serializados
(dict, tupla, dataclass congelada), nunca objetos ORM presos a uma sessão.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any, Awaitable, Callable, Dict, Hashable, Optional, Tuple

DEFAULT_TTL_SECONDS = 300.0

_MISSING = object()


class AsyncTTLCache:
    def __init__(self, name: str, ttl_seconds: float = DEFAULT_TTL_SECONDS) -> None:
        self.name = name
        self.ttl = ttl_seconds
        self._data: Dict[Hashable, Tuple[float, Any]] = {}
        self._lock = asyncio.Lock()
        self.hits = 0
        self.misses = 0

    def _now(self) -> float:
        return time.monotonic()

    def get(self, key: Hashable) -> Any:
        """Valor vivo ou `None`-sentinela `_MISSING` (uso interno)."""
        entry = self._data.get(key)
        if entry is None:
            return _MISSING
        expires_at, value = entry
        if self._now() >= expires_at:
            self._data.pop(key, None)
            return _MISSING
        return value

    def set(self, key: Hashable, value: Any) -> None:
        self._data[key] = (self._now() + self.ttl, value)

    async def get_or_load(self, key: Hashable, loader: Callable[[], Awaitable[Any]]) -> Any:
        value = self.get(key)
        if value is not _MISSING:
            self.hits += 1
            return value
        # Lock: várias requisições frias ao mesmo tempo fazem UMA consulta só.
        async with self._lock:
            value = self.get(key)
            if value is not _MISSING:
                self.hits += 1
                return value
            self.misses += 1
            value = await loader()
            self.set(key, value)
            return value

    def invalidate(self, key: Optional[Hashable] = None) -> None:
        if key is None:
            self._data.clear()
        else:
            self._data.pop(key, None)


# Caches globais da aplicação.
plans_cache = AsyncTTLCache("plans")
obligation_rules_cache = AsyncTTLCache("obligation_rules")

_ALL = (plans_cache, obligation_rules_cache)


def invalidate_all() -> None:
    for cache in _ALL:
        cache.invalidate()
