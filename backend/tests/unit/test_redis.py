"""
Unit Tests for Redis Utilities

Tests the Redis cache, session store, and task queue utilities.
All Redis operations are mocked for fast, isolated testing.

These tests verify:
- RedisCache key generation and operations
- SessionStore lifecycle (create, get, update, delete)
- TaskQueue enqueue/dequeue operations
- TTL handling
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestRedisCache:
    """Test suite for RedisCache class."""

    @pytest.fixture
    def cache(self):
        """Create a RedisCache instance."""
        from app.db.redis import RedisCache

        return RedisCache(prefix="test_cache")

    @pytest.mark.asyncio
    async def test_cache_key_generation(self, cache) -> None:
        """Cache keys should be properly namespaced."""
        key = cache._make_key("test_func", ("arg1", "arg2"), {"key": "value"})

        assert key.startswith("test_cache:test_func:")
        # Key should contain a hash suffix
        assert len(key) > len("test_cache:test_func:")

    @pytest.mark.asyncio
    async def test_cache_key_deterministic(self, cache) -> None:
        """Same arguments should produce same cache key."""
        key1 = cache._make_key("func", ("a", "b"), {"x": 1})
        key2 = cache._make_key("func", ("a", "b"), {"x": 1})

        assert key1 == key2

    @pytest.mark.asyncio
    async def test_cache_key_different_for_different_args(self, cache) -> None:
        """Different arguments should produce different keys."""
        key1 = cache._make_key("func", ("a",), {})
        key2 = cache._make_key("func", ("b",), {})

        assert key1 != key2

    @pytest.mark.asyncio
    async def test_cache_get_returns_none_for_missing_key(
        self, cache, mock_redis
    ) -> None:
        """get should return None for non-existent keys."""
        with patch("app.db.redis.get_redis", return_value=mock_redis):
            mock_redis.get = AsyncMock(return_value=None)

            result = await cache.get("nonexistent")

            assert result is None

    @pytest.mark.asyncio
    async def test_cache_get_returns_deserialized_value(
        self, cache, mock_redis
    ) -> None:
        """get should deserialize JSON values from Redis."""
        with patch("app.db.redis.get_redis", return_value=mock_redis):
            stored_value = {"data": "test", "count": 42}
            mock_redis.get = AsyncMock(return_value=json.dumps(stored_value))

            result = await cache.get("existing_key")

            assert result == stored_value

    @pytest.mark.asyncio
    async def test_cache_set_serializes_value(self, cache, mock_redis) -> None:
        """set should serialize values as JSON."""
        with patch("app.db.redis.get_redis", return_value=mock_redis):
            value = {"key": "value", "number": 123}

            await cache.set("test_key", value, ttl=300)

            mock_redis.setex.assert_called_once()
            call_args = mock_redis.setex.call_args
            assert call_args[0][0] == "test_cache:test_key"
            assert call_args[0][1] == 300
            assert json.loads(call_args[0][2]) == value

    @pytest.mark.asyncio
    async def test_cache_delete_removes_key(self, cache, mock_redis) -> None:
        """delete should remove the key from Redis."""
        with patch("app.db.redis.get_redis", return_value=mock_redis):
            await cache.delete("test_key")

            mock_redis.delete.assert_called_once_with("test_cache:test_key")

    @pytest.mark.asyncio
    async def test_cache_clear_pattern(self, cache, mock_redis) -> None:
        """clear_pattern should delete all matching keys."""
        with patch("app.db.redis.get_redis", return_value=mock_redis):
            mock_redis.keys = AsyncMock(
                return_value=["test_cache:user:1", "test_cache:user:2"]
            )

            await cache.clear_pattern("user:*")

            mock_redis.keys.assert_called_once_with("test_cache:user:*")
            mock_redis.delete.assert_called_once_with(
                "test_cache:user:1", "test_cache:user:2"
            )


class TestRedisCacheDecorator:
    """Test suite for the @cached decorator."""

    @pytest.mark.asyncio
    async def test_cached_decorator_caches_result(self, mock_redis) -> None:
        """Decorated function results should be cached."""
        from app.db.redis import RedisCache

        cache = RedisCache(prefix="test")
        call_count = 0

        with patch("app.db.redis.get_redis", return_value=mock_redis):
            mock_redis.get = AsyncMock(return_value=None)  # Cache miss

            @cache.cached(ttl=60)
            async def expensive_function(x: int) -> dict:
                nonlocal call_count
                call_count += 1
                return {"result": x * 2}

            result = await expensive_function(5)

            assert result == {"result": 10}
            assert call_count == 1
            mock_redis.setex.assert_called_once()

    @pytest.mark.asyncio
    async def test_cached_decorator_returns_cached_value(self, mock_redis) -> None:
        """Decorated function should return cached value on hit."""
        from app.db.redis import RedisCache

        cache = RedisCache(prefix="test")
        call_count = 0

        with patch("app.db.redis.get_redis", return_value=mock_redis):
            cached_result = {"result": 100}
            mock_redis.get = AsyncMock(return_value=json.dumps(cached_result))

            @cache.cached(ttl=60)
            async def expensive_function(x: int) -> dict:
                nonlocal call_count
                call_count += 1
                return {"result": x * 2}

            result = await expensive_function(50)

            assert result == cached_result
            assert call_count == 0  # Function not called due to cache hit


class TestSessionStore:
    """Test suite for SessionStore class."""

    @pytest.fixture
    def session_store(self):
        """Create a SessionStore instance."""
        from app.db.redis import SessionStore

        return SessionStore(prefix="test_session")

    @pytest.mark.asyncio
    async def test_create_session(self, session_store, mock_redis) -> None:
        """create_session should store session data with TTL."""
        with patch("app.db.redis.get_redis", return_value=mock_redis):
            session_data = {"user_id": "123", "email": "test@example.com"}

            result = await session_store.create_session("session_id", session_data)

            assert result == "session_id"
            mock_redis.setex.assert_called_once()
            call_args = mock_redis.setex.call_args
            assert call_args[0][0] == "test_session:session_id"
            assert json.loads(call_args[0][2]) == session_data

    @pytest.mark.asyncio
    async def test_get_session_returns_data(self, session_store, mock_redis) -> None:
        """get_session should return session data and refresh TTL."""
        with patch("app.db.redis.get_redis", return_value=mock_redis):
            session_data = {"user_id": "123", "email": "test@example.com"}
            mock_redis.get = AsyncMock(return_value=json.dumps(session_data))

            result = await session_store.get_session("session_id")

            assert result == session_data
            mock_redis.expire.assert_called_once()  # TTL should be refreshed

    @pytest.mark.asyncio
    async def test_get_session_returns_none_for_expired(
        self, session_store, mock_redis
    ) -> None:
        """get_session should return None for expired sessions."""
        with patch("app.db.redis.get_redis", return_value=mock_redis):
            mock_redis.get = AsyncMock(return_value=None)

            result = await session_store.get_session("expired_session")

            assert result is None

    @pytest.mark.asyncio
    async def test_update_session(self, session_store, mock_redis) -> None:
        """update_session should replace session data if exists."""
        with patch("app.db.redis.get_redis", return_value=mock_redis):
            mock_redis.exists = AsyncMock(return_value=1)
            new_data = {"user_id": "123", "email": "new@example.com"}

            await session_store.update_session("session_id", new_data)

            mock_redis.setex.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_session_noop_if_not_exists(
        self, session_store, mock_redis
    ) -> None:
        """update_session should not create session if it doesn't exist."""
        with patch("app.db.redis.get_redis", return_value=mock_redis):
            mock_redis.exists = AsyncMock(return_value=0)

            await session_store.update_session("nonexistent", {"data": "test"})

            mock_redis.setex.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_session(self, session_store, mock_redis) -> None:
        """delete_session should remove session from Redis."""
        with patch("app.db.redis.get_redis", return_value=mock_redis):
            await session_store.delete_session("session_id")

            mock_redis.delete.assert_called_once_with("test_session:session_id")

    @pytest.mark.asyncio
    async def test_refresh_session(self, session_store, mock_redis) -> None:
        """refresh_session should reset TTL."""
        with patch("app.db.redis.get_redis", return_value=mock_redis):
            await session_store.refresh_session("session_id", ttl=7200)

            mock_redis.expire.assert_called_once_with("test_session:session_id", 7200)


class TestTaskQueue:
    """Test suite for TaskQueue class."""

    @pytest.fixture
    def task_queue(self):
        """Create a TaskQueue instance."""
        from app.db.redis import TaskQueue

        return TaskQueue(queue_name="test_tasks")

    @pytest.mark.asyncio
    async def test_enqueue_task(self, task_queue, mock_redis) -> None:
        """enqueue should add task to queue."""
        with patch("app.db.redis.get_redis", return_value=mock_redis):
            await task_queue.enqueue("process_document", {"doc_id": "123"})

            mock_redis.rpush.assert_called_once()
            call_args = mock_redis.rpush.call_args
            assert call_args[0][0] == "test_tasks"
            task_data = json.loads(call_args[0][1])
            assert task_data["type"] == "process_document"
            assert task_data["payload"] == {"doc_id": "123"}

    @pytest.mark.asyncio
    async def test_dequeue_nonblocking_returns_task(
        self, task_queue, mock_redis
    ) -> None:
        """dequeue with timeout=0 should use LPOP."""
        with patch("app.db.redis.get_redis", return_value=mock_redis):
            task = {"type": "test", "payload": {"data": 1}}
            mock_redis.lpop = AsyncMock(return_value=json.dumps(task))

            result = await task_queue.dequeue(timeout=0)

            assert result == task
            mock_redis.lpop.assert_called_once_with("test_tasks")

    @pytest.mark.asyncio
    async def test_dequeue_nonblocking_returns_none_if_empty(
        self, task_queue, mock_redis
    ) -> None:
        """dequeue should return None if queue is empty."""
        with patch("app.db.redis.get_redis", return_value=mock_redis):
            mock_redis.lpop = AsyncMock(return_value=None)

            result = await task_queue.dequeue(timeout=0)

            assert result is None

    @pytest.mark.asyncio
    async def test_dequeue_blocking_uses_blpop(self, task_queue, mock_redis) -> None:
        """dequeue with timeout>0 should use BLPOP."""
        with patch("app.db.redis.get_redis", return_value=mock_redis):
            task = {"type": "test", "payload": {}}
            mock_redis.blpop = AsyncMock(return_value=("test_tasks", json.dumps(task)))

            result = await task_queue.dequeue(timeout=30)

            assert result == task
            mock_redis.blpop.assert_called_once_with("test_tasks", timeout=30)

    @pytest.mark.asyncio
    async def test_dequeue_blocking_returns_none_on_timeout(
        self, task_queue, mock_redis
    ) -> None:
        """dequeue should return None if BLPOP times out."""
        with patch("app.db.redis.get_redis", return_value=mock_redis):
            mock_redis.blpop = AsyncMock(return_value=None)

            result = await task_queue.dequeue(timeout=30)

            assert result is None

    @pytest.mark.asyncio
    async def test_queue_length(self, task_queue, mock_redis) -> None:
        """length should return number of tasks in queue."""
        with patch("app.db.redis.get_redis", return_value=mock_redis):
            mock_redis.llen = AsyncMock(return_value=5)

            result = await task_queue.length()

            assert result == 5
            mock_redis.llen.assert_called_once_with("test_tasks")


class TestGlobalInstances:
    """Test global Redis utility instances."""

    def test_global_cache_exists(self) -> None:
        """Global cache instance should be importable."""
        from app.db.redis import cache

        assert cache is not None
        assert cache.prefix == "cache"

    def test_global_session_store_exists(self) -> None:
        """Global session_store instance should be importable."""
        from app.db.redis import session_store

        assert session_store is not None
        assert session_store.prefix == "session"

    def test_global_task_queue_exists(self) -> None:
        """Global task_queue instance should be importable."""
        from app.db.redis import task_queue

        assert task_queue is not None
        assert task_queue.queue_name == "tasks"


class TestRedisConnectionPool:
    """Test Redis connection pool management."""

    @pytest.mark.asyncio
    async def test_get_redis_returns_client(self) -> None:
        """get_redis should return a Redis client."""
        from app.db.redis import get_redis

        with patch("app.db.redis.get_redis_pool") as mock_pool:
            mock_pool.return_value = MagicMock()

            client = await get_redis()

            assert client is not None

    @pytest.mark.asyncio
    async def test_close_redis_pool(self) -> None:
        """close_redis_pool should disconnect the pool."""
        from app.db import redis as redis_module

        # Set up a mock pool
        mock_pool = MagicMock()
        mock_pool.disconnect = AsyncMock()
        redis_module._redis_pool = mock_pool

        await redis_module.close_redis_pool()

        mock_pool.disconnect.assert_called_once()
        assert redis_module._redis_pool is None
