"""Rate limit e OTP compartilhados via Redis (SEC-4/SEC-7): valem entre instâncias."""

import pytest
from fastapi import HTTPException

from app.api.v1.endpoints import auth
from app.core.auth_rate_limiter import OTP_MAX_ATTEMPTS, _RedisAuthRateLimiter


class FakeRedis:
    """Só o que o limiter e o OTP usam (TTL simulado como 'tem/não tem')."""

    def __init__(self):
        self.d, self.ttls = {}, {}

    def incr(self, k):
        self.d[k] = int(self.d.get(k, 0)) + 1
        return self.d[k]

    def expire(self, k, s):
        self.ttls[k] = s

    def set(self, k, v, ex=None):
        self.d[k] = v
        self.ttls[k] = ex

    def get(self, k):
        return self.d.get(k)

    def ttl(self, k):
        return self.ttls.get(k, -2) if k in self.d else -2

    def delete(self, *ks):
        return sum(1 for k in ks if self.d.pop(k, None) is not None)


class Down:
    def __getattr__(self, _):
        def boom(*a, **k):
            raise ConnectionError("redis fora")

        return boom


def test_duas_instancias_somam_tentativas():
    r = FakeRedis()
    a, b = _RedisAuthRateLimiter(r), _RedisAuthRateLimiter(r)
    for i in range(OTP_MAX_ATTEMPTS):
        (a if i % 2 else b).record_otp_failure("u1")
    with pytest.raises(HTTPException) as exc:
        a.check_otp_user("u1")
    assert exc.value.status_code == 429
    b.record_otp_success("u1")
    a.check_otp_user("u1")


def test_redis_fora_cai_para_memoria():
    lim = _RedisAuthRateLimiter(Down())
    for _ in range(OTP_MAX_ATTEMPTS):
        lim.record_otp_failure("u2")
    with pytest.raises(HTTPException):
        lim.check_otp_user("u2")


def test_otp_email_no_redis_e_uso_unico(monkeypatch):
    monkeypatch.setattr(auth, "_otp_redis", FakeRedis())
    code = auth._generate_email_otp("u3")
    assert not auth._verify_email_otp("u3", "000000" if code != "000000" else "111111")
    assert auth._verify_email_otp("u3", code)
    assert not auth._verify_email_otp("u3", code)
