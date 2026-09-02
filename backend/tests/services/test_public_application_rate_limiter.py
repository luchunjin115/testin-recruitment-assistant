from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, Mock

from redis.exceptions import ConnectionError

from app.services.public_application_rate_limiter import (
    PublicApplicationRateLimitExceededError,
    PublicApplicationRateLimitUnavailableError,
    PublicApplicationRateLimiter,
)


class PublicApplicationRateLimiterTest(IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.redis = Mock()
        self.redis.eval = AsyncMock(side_effect=[1, 2, 3])
        self.redis.ttl = AsyncMock(return_value=19)
        self.limiter = PublicApplicationRateLimiter()

    async def check(self, *, per_contact: int = 3) -> None:
        await self.limiter.check(
            self.redis,
            client_ip="127.0.0.1",
            phone="13800000001",
            email="candidate@example.com",
            window_seconds=60,
            per_ip=10,
            per_contact=per_contact,
        )

    async def test_hashes_ip_and_contacts_before_writing_rate_keys(self) -> None:
        await self.check()

        keys = [call.args[2] for call in self.redis.eval.await_args_list]
        self.assertEqual(len(keys), 3)
        self.assertTrue(all(len(key.rsplit(":", 1)[-1]) == 64 for key in keys))
        self.assertNotIn("127.0.0.1", " ".join(keys))
        self.assertNotIn("13800000001", " ".join(keys))
        self.assertNotIn("candidate@example.com", " ".join(keys))

    async def test_limit_exceeded_returns_positive_retry_after(self) -> None:
        self.redis.eval.side_effect = [1, 4]

        with self.assertRaises(PublicApplicationRateLimitExceededError) as raised:
            await self.check(per_contact=3)

        self.assertEqual(raised.exception.retry_after, 19)

    async def test_redis_failure_is_fail_closed_unavailable(self) -> None:
        self.redis.eval.side_effect = ConnectionError("redis://secret")

        with self.assertRaises(PublicApplicationRateLimitUnavailableError):
            await self.check()
