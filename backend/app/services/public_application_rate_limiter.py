from __future__ import annotations

import hashlib
from dataclasses import dataclass

from redis.asyncio import Redis
from redis.exceptions import RedisError


_INCREMENT_WITH_TTL = """
local count = redis.call('INCR', KEYS[1])
if count == 1 then
  redis.call('EXPIRE', KEYS[1], ARGV[1])
end
return count
"""


class PublicApplicationRateLimitUnavailableError(RuntimeError):
    pass


@dataclass(frozen=True)
class PublicApplicationRateLimitExceededError(RuntimeError):
    retry_after: int


class PublicApplicationRateLimiter:
    async def check(
        self,
        redis: Redis,
        *,
        client_ip: str,
        phone: str,
        email: str,
        window_seconds: int,
        per_ip: int,
        per_contact: int,
    ) -> None:
        dimensions = (
            ("ip", client_ip, per_ip),
            ("phone", phone, per_contact),
            ("email", email, per_contact),
        )
        try:
            for dimension, value, limit in dimensions:
                key = self._key(dimension, value)
                count = int(
                    await redis.eval(
                        _INCREMENT_WITH_TTL,
                        1,
                        key,
                        window_seconds,
                    )
                )
                if count > limit:
                    ttl = int(await redis.ttl(key))
                    raise PublicApplicationRateLimitExceededError(
                        retry_after=max(ttl, 1)
                    )
        except PublicApplicationRateLimitExceededError:
            raise
        except (RedisError, OSError, TimeoutError, ValueError, TypeError) as exc:
            raise PublicApplicationRateLimitUnavailableError() from exc

    @staticmethod
    def _key(dimension: str, value: str) -> str:
        digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
        return f"public-application:rate:{dimension}:{digest}"


public_application_rate_limiter = PublicApplicationRateLimiter()
