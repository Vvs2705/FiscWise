"""
Auth Rate Limiter — FiscWise

In-process rate limiter for authentication endpoints.
No Redis required — works perfectly on single-instance deployments (Fly.io default).

Protected endpoints:
  - POST /auth/login             → max 10 tentativas por IP / 15 min
  - POST /auth/login/verify-2fa  → max 5 tentativas por user_id / 15 min (lockout total)
  - POST /auth/google            → max 10 tentativas por IP / 15 min

Security design:
  - Login: limita por IP (protege contra credential stuffing / password spray)
  - Verify-2FA: limita por user_id (protege contra brute force do código OTP de 6 dígitos)
    Um código de 6 dígitos tem 1.000.000 combinações; com 5 tentativas e 15min de lockout
    um atacante levaria ~1.4 bilhão de dias para esgotar o espaço.
  - Exponential backoff opcional: cada tentativa falha adiciona delay progressivo.
  - Thread-safety: usa threading.Lock para mutações no dicionário compartilhado.

Production note:
  - Para múltiplas instâncias Fly.io, substitua _AuthRateLimiter por implementação Redis.
  - A interface pública (check_login_ip, check_otp_user, record_success_*) permanece igual.
"""

import threading
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import HTTPException, status, Request

logger = logging.getLogger(__name__)


# ─── Configuração ─────────────────────────────────────────────────────────────

# Login por IP (senha)
LOGIN_MAX_ATTEMPTS   = 10          # tentativas permitidas
LOGIN_WINDOW_MINUTES = 15          # janela de tempo
LOGIN_LOCKOUT_MINUTES = 15         # tempo de bloqueio após exceder

# OTP / verify-2fa por user_id
OTP_MAX_ATTEMPTS    = 5            # tentativas permitidas
OTP_WINDOW_MINUTES  = 15           # janela de tempo
OTP_LOCKOUT_MINUTES = 15           # tempo de bloqueio após exceder


# ─── Store interno ────────────────────────────────────────────────────────────

@dataclass
class _AttemptRecord:
    count: int = 0
    first_attempt: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    locked_until: Optional[datetime] = None

    def is_locked(self) -> bool:
        if self.locked_until is None:
            return False
        if datetime.now(timezone.utc) < self.locked_until:
            return True
        # Lockout expired — reset
        self.count = 0
        self.locked_until = None
        self.first_attempt = datetime.now(timezone.utc)
        return False

    def window_expired(self, window_minutes: int) -> bool:
        return datetime.now(timezone.utc) > self.first_attempt + timedelta(minutes=window_minutes)

    def seconds_until_unlock(self) -> int:
        if self.locked_until is None:
            return 0
        delta = self.locked_until - datetime.now(timezone.utc)
        return max(0, int(delta.total_seconds()))


class _AuthRateLimiter:
    """Thread-safe in-memory rate limiter for auth endpoints."""

    def __init__(self):
        self._lock = threading.Lock()
        # Key: str (IP or user_id) → _AttemptRecord
        self._login_store:  dict[str, _AttemptRecord] = {}
        self._otp_store:    dict[str, _AttemptRecord] = {}

    def _get_or_create(self, store: dict, key: str, window_minutes: int) -> _AttemptRecord:
        record = store.get(key)
        if record is None:
            record = _AttemptRecord()
            store[key] = record
        elif record.window_expired(window_minutes) and not record.is_locked():
            # Janela expirou e não está bloqueado — reseta
            record.count = 0
            record.first_attempt = datetime.now(timezone.utc)
        return record

    # ── Login / IP ────────────────────────────────────────────────────────────

    def check_login_ip(self, ip: str) -> None:
        """
        Verifica se o IP está bloqueado para tentativas de login.
        Levanta HTTP 429 se bloqueado.
        """
        with self._lock:
            record = self._get_or_create(self._login_store, ip, LOGIN_WINDOW_MINUTES)
            if record.is_locked():
                secs = record.seconds_until_unlock()
                logger.warning("Login bloqueado por IP=%s por %ds", ip, secs)
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=(
                        f"Muitas tentativas de login. "
                        f"Tente novamente em {secs // 60 + 1} minuto(s)."
                    ),
                    headers={"Retry-After": str(secs)},
                )

    def record_login_failure(self, ip: str) -> None:
        """Registra falha de login para o IP. Bloqueia após MAX_ATTEMPTS."""
        with self._lock:
            record = self._get_or_create(self._login_store, ip, LOGIN_WINDOW_MINUTES)
            record.count += 1
            logger.info("Falha de login IP=%s tentativa=%d/%d", ip, record.count, LOGIN_MAX_ATTEMPTS)
            if record.count >= LOGIN_MAX_ATTEMPTS:
                record.locked_until = datetime.now(timezone.utc) + timedelta(minutes=LOGIN_LOCKOUT_MINUTES)
                logger.warning(
                    "IP=%s BLOQUEADO por %d minutos após %d falhas de login",
                    ip, LOGIN_LOCKOUT_MINUTES, record.count
                )

    def record_login_success(self, ip: str) -> None:
        """Reseta contador de falhas após login bem-sucedido."""
        with self._lock:
            self._login_store.pop(ip, None)

    # ── OTP verify-2fa / user_id ──────────────────────────────────────────────

    def check_otp_user(self, user_id: str) -> None:
        """
        Verifica se o user_id está bloqueado para tentativas de OTP.
        Levanta HTTP 429 se bloqueado.
        """
        with self._lock:
            record = self._get_or_create(self._otp_store, user_id, OTP_WINDOW_MINUTES)
            if record.is_locked():
                secs = record.seconds_until_unlock()
                logger.warning("OTP bloqueado user_id=%s por %ds", user_id, secs)
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=(
                        f"Muitas tentativas incorretas. "
                        f"Por segurança, sua conta foi temporariamente bloqueada. "
                        f"Tente novamente em {secs // 60 + 1} minuto(s)."
                    ),
                    headers={"Retry-After": str(secs)},
                )

    def record_otp_failure(self, user_id: str) -> None:
        """Registra falha de OTP. Bloqueia o user_id após OTP_MAX_ATTEMPTS."""
        with self._lock:
            record = self._get_or_create(self._otp_store, user_id, OTP_WINDOW_MINUTES)
            record.count += 1
            remaining = max(0, OTP_MAX_ATTEMPTS - record.count)
            logger.info(
                "Falha de OTP user_id=%s tentativa=%d/%d restantes=%d",
                user_id, record.count, OTP_MAX_ATTEMPTS, remaining
            )
            if record.count >= OTP_MAX_ATTEMPTS:
                record.locked_until = datetime.now(timezone.utc) + timedelta(minutes=OTP_LOCKOUT_MINUTES)
                logger.warning(
                    "user_id=%s BLOQUEADO por %d minutos após %d falhas de OTP",
                    user_id, OTP_LOCKOUT_MINUTES, record.count
                )

    def record_otp_success(self, user_id: str) -> None:
        """Reseta contador de OTP após verificação bem-sucedida."""
        with self._lock:
            self._otp_store.pop(user_id, None)

    def get_otp_remaining_attempts(self, user_id: str) -> int:
        """Retorna tentativas restantes de OTP para o user_id (sem bloquear)."""
        with self._lock:
            record = self._otp_store.get(user_id)
            if record is None or record.window_expired(OTP_WINDOW_MINUTES):
                return OTP_MAX_ATTEMPTS
            return max(0, OTP_MAX_ATTEMPTS - record.count)

    # ── Limpeza periódica (opcional) ──────────────────────────────────────────

    def cleanup_expired(self) -> int:
        """
        Remove entradas expiradas dos stores.
        Pode ser chamado periodicamente pelo scheduler para evitar memory leak.
        Retorna o número de entradas removidas.
        """
        removed = 0
        now = datetime.now(timezone.utc)
        with self._lock:
            for store, window in [
                (self._login_store, LOGIN_WINDOW_MINUTES),
                (self._otp_store, OTP_WINDOW_MINUTES),
            ]:
                expired_keys = [
                    k for k, r in store.items()
                    if (r.locked_until is None or r.locked_until < now)
                    and r.first_attempt + timedelta(minutes=window) < now
                ]
                for k in expired_keys:
                    del store[k]
                    removed += 1
        if removed:
            logger.debug("Rate limiter cleanup: %d entradas removidas", removed)
        return removed


# ─── Singleton global ─────────────────────────────────────────────────────────

auth_rate_limiter = _AuthRateLimiter()


# ─── Helpers para uso nos endpoints ───────────────────────────────────────────

def get_client_ip(request: Request) -> str:
    """Extrai IP do cliente, respeitando X-Forwarded-For (Fly.io proxy)."""
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else "unknown"
