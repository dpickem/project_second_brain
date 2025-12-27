"""
Redis Connection and Utilities

Provides Redis connection pooling, caching utilities, and session management.

Usage:
    from app.db.redis import get_redis, RedisCache, SessionStore

    # Get Redis connection
    redis = await get_redis()
    await redis.set("key", "value")

    # Use caching decorator
    cache = RedisCache()

    @cache.cached(ttl=300)
    async def get_data():
        ...

    # Session management
    session_store = SessionStore()
    await session_store.create_session(user_id, data)
"""

import hashlib
import json
from functools import wraps
from typing import Any, Callable, Optional

import redis.asyncio as redis

from app.config import settings, yaml_config


# Get Redis configuration from yaml config
redis_config: dict[str, Any] = yaml_config.get("redis", {})
DEFAULT_CACHE_TTL: int = redis_config.get("cache_ttl", 300)
DEFAULT_SESSION_TTL: int = redis_config.get("session_ttl", 3600)


# Connection pool (lazily initialized)
_redis_pool: Optional[redis.ConnectionPool] = None


async def get_redis_pool() -> redis.ConnectionPool:
    """Get or create the Redis connection pool."""
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = redis.ConnectionPool.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            max_connections=10,
        )
    return _redis_pool


async def get_redis() -> redis.Redis:
    """
    Get a Redis connection from the pool.

    Usage:
        redis = await get_redis()
        await redis.set("key", "value")
    """
    pool = await get_redis_pool()
    return redis.Redis(connection_pool=pool)


async def close_redis_pool() -> None:
    """Close the Redis connection pool."""
    global _redis_pool
    if _redis_pool is not None:
        await _redis_pool.disconnect()
        _redis_pool = None


class RedisCache:
    """
    Redis-based caching utilities.

    Provides a decorator for caching function results and
    manual cache management methods.
    """

    def __init__(self, prefix: str = "cache") -> None:
        self.prefix = prefix

    def _make_key(
        self, func_name: str, args: tuple[Any, ...], kwargs: dict[str, Any]
    ) -> str:
        """Generate a cache key from function name and arguments."""
        key_data = f"{func_name}:{args}:{sorted(kwargs.items())}"
        key_hash = hashlib.md5(key_data.encode()).hexdigest()[:16]
        return f"{self.prefix}:{func_name}:{key_hash}"

    def cached(
        self, ttl: int = DEFAULT_CACHE_TTL
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """
        Decorator to cache function results in Redis.

        Usage:
            cache = RedisCache()

            @cache.cached(ttl=300)
            async def expensive_operation(arg1, arg2):
                ...
        """

        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            @wraps(func)
            async def wrapper(*args: Any, **kwargs: Any) -> Any:
                r = await get_redis()
                cache_key = self._make_key(func.__name__, args, kwargs)

                # Try to get from cache
                cached = await r.get(cache_key)
                if cached is not None:
                    return json.loads(cached)

                # Call function and cache result
                result = await func(*args, **kwargs)
                await r.setex(cache_key, ttl, json.dumps(result))

                return result

            return wrapper

        return decorator

    async def get(self, key: str) -> Optional[Any]:
        """Get a value from cache."""
        r = await get_redis()
        full_key = f"{self.prefix}:{key}"
        value = await r.get(full_key)
        if value:
            return json.loads(value)
        return None

    async def set(self, key: str, value: Any, ttl: int = DEFAULT_CACHE_TTL) -> None:
        """Set a value in cache."""
        r = await get_redis()
        full_key = f"{self.prefix}:{key}"
        await r.setex(full_key, ttl, json.dumps(value))

    async def delete(self, key: str) -> None:
        """Delete a value from cache."""
        r = await get_redis()
        full_key = f"{self.prefix}:{key}"
        await r.delete(full_key)

    async def clear_pattern(self, pattern: str) -> None:
        """Clear all keys matching a pattern."""
        r = await get_redis()
        full_pattern = f"{self.prefix}:{pattern}"
        keys = await r.keys(full_pattern)
        if keys:
            await r.delete(*keys)


class SessionStore:
    """
    Redis-based session storage for managing user authentication state.

    Purpose:
        Sessions allow the API to remember who a user is across multiple requests
        without requiring them to authenticate on every single request. When a user
        logs in, a session is created containing their identity and permissions.
        Subsequent requests include a session token that maps back to this data.

    Why Redis?
        - **Speed**: Session lookups happen on every authenticated request, so they
          must be fast. Redis stores data in memory, providing sub-millisecond access.
        - **Automatic expiration**: Redis TTL (time-to-live) automatically cleans up
          expired sessions without manual garbage collection.
        - **Scalability**: Multiple API server instances can share the same Redis,
          enabling horizontal scaling without sticky sessions.
        - **Persistence**: Redis can persist data to disk, surviving server restarts.

    Session Lifecycle:
        1. User authenticates (login) → create_session() stores user data
        2. User makes requests → get_session() retrieves and validates session
        3. User activity → TTL is refreshed on access (sliding expiration)
        4. User logs out → delete_session() removes the session
        5. User inactive → Redis automatically expires the session after TTL

    Typical Session Data:
        {
            "user_id": "uuid-here",
            "email": "user@example.com",
            "roles": ["user", "admin"],
            "preferences": {...},
            "login_time": "2024-01-15T10:30:00Z"
        }

    Usage:
        # Create session on login
        session_id = str(uuid4())
        await session_store.create_session(session_id, {
            "user_id": user.id,
            "email": user.email,
            "roles": user.roles
        })
        # Return session_id as a cookie or token to the client

        # Validate session on subsequent requests
        session = await session_store.get_session(session_id)
        if session is None:
            raise HTTPException(401, "Session expired")

        # Logout
        await session_store.delete_session(session_id)
    """

    def __init__(self, prefix: str = "session") -> None:
        """
        Initialize the session store.

        Args:
            prefix: Redis key prefix for namespacing (default: "session").
                    Keys are stored as "{prefix}:{session_id}".
        """
        self.prefix = prefix
        self.ttl = DEFAULT_SESSION_TTL

    def _make_key(self, session_id: str) -> str:
        """Generate a namespaced Redis key for a session."""
        return f"{self.prefix}:{session_id}"

    async def create_session(self, session_id: str, data: dict[str, Any]) -> str:
        """
        Create a new session with the given data.

        The session will automatically expire after DEFAULT_SESSION_TTL seconds
        of inactivity (configurable in config/default.yaml).

        Args:
            session_id: Unique identifier for the session (typically a UUID).
            data: Dictionary of session data (user info, permissions, etc.).

        Returns:
            The session_id (for convenience in chaining).
        """
        r = await get_redis()
        key = self._make_key(session_id)
        await r.setex(key, self.ttl, json.dumps(data))
        return session_id

    async def get_session(self, session_id: str) -> Optional[dict[str, Any]]:
        """
        Retrieve session data and refresh its expiration (sliding window).

        Each successful access resets the TTL, keeping active sessions alive
        while allowing inactive ones to expire naturally.

        Args:
            session_id: The session identifier to look up.

        Returns:
            Session data dictionary if found, None if expired or not found.
        """
        r = await get_redis()
        key = self._make_key(session_id)
        data = await r.get(key)
        if data:
            # Refresh TTL on access (sliding expiration)
            await r.expire(key, self.ttl)
            return json.loads(data)
        return None

    async def update_session(self, session_id: str, data: dict[str, Any]) -> None:
        """
        Replace session data with new values.

        Only updates if the session still exists (not expired).
        Use this to update user preferences or permissions mid-session.

        Args:
            session_id: The session identifier to update.
            data: New session data (completely replaces existing data).
        """
        r = await get_redis()
        key = self._make_key(session_id)
        if await r.exists(key):
            await r.setex(key, self.ttl, json.dumps(data))

    async def delete_session(self, session_id: str) -> None:
        """
        Explicitly delete a session (logout).

        Immediately invalidates the session rather than waiting for expiration.

        Args:
            session_id: The session identifier to delete.
        """
        r = await get_redis()
        key = self._make_key(session_id)
        await r.delete(key)

    async def refresh_session(self, session_id: str, ttl: Optional[int] = None) -> None:
        """
        Reset a session's expiration time to a new TTL.

        This sets an absolute TTL (not additive). For example, if a session
        has 500 seconds remaining and you call refresh_session(id, 3600),
        the new TTL becomes 3600 seconds.

        Why use r.expire() instead of r.setex()?
            - expire() only updates the TTL without touching the data
            - setex() would require fetching the data first to re-save it
            - More efficient when you just want to keep a session alive

        Use cases:
            - "Remember me" functionality (set longer TTL on login)
            - Keep session alive during long-running operations
            - Reset to default TTL after important actions

        Args:
            session_id: The session identifier to refresh.
            ttl: New TTL in seconds. If None, uses the default session TTL.
        """
        r = await get_redis()
        key = self._make_key(session_id)
        new_ttl = ttl or self.ttl
        await r.expire(key, new_ttl)


class TaskQueue:
    """
    Simple Redis-based task queue.

    For lightweight background task management.
    For production, consider using Celery or similar.
    """

    def __init__(self, queue_name: str = "tasks") -> None:
        self.queue_name = queue_name

    async def enqueue(self, task_type: str, payload: dict[str, Any]) -> None:
        """Add a task to the queue."""
        r = await get_redis()
        task = json.dumps({"type": task_type, "payload": payload})
        await r.rpush(self.queue_name, task)

    async def dequeue(self, timeout: int = 0) -> Optional[dict[str, Any]]:
        """
        Get and remove the next task from the queue (FIFO order).

        This method has two modes based on the timeout parameter:

        1. Non-blocking (timeout=0, default):
           Uses LPOP to immediately pop the leftmost item from the list.
           - If queue is empty: returns None immediately
           - If queue has items: returns the oldest task and removes it

        2. Blocking (timeout > 0):
           Uses BLPOP to wait for a task if the queue is empty.
           - If queue is empty: blocks up to `timeout` seconds waiting for a task
           - If queue has items: returns immediately with the oldest task
           - If timeout expires with no task: returns None

        Why two different Redis commands?
           - LPOP: Fast, non-blocking, but returns None on empty queue
           - BLPOP: Efficient blocking wait (no CPU polling), perfect for workers

        BLPOP return format:
           Returns a tuple (queue_name, value) because BLPOP can wait on multiple
           queues. We use result[1] to get just the value.

        Queue structure (FIFO):
           enqueue() uses RPUSH (add to right/end)
           dequeue() uses LPOP/BLPOP (remove from left/front)

           [oldest] <-- LPOP    [task2] [task3] [newest] <-- RPUSH

        Args:
            timeout: Seconds to wait for a task.
                     0 = return immediately (non-blocking)
                     >0 = block up to this many seconds

        Returns:
            Task dictionary {"type": str, "payload": dict} or None if no task.

        Example:
            # Non-blocking check (for polling)
            task = await queue.dequeue()

            # Blocking worker loop (efficient, no polling)
            while True:
                task = await queue.dequeue(timeout=30)
                if task:
                    await process_task(task)
        """
        r = await get_redis()
        if timeout > 0:
            # BLPOP blocks until a task is available or timeout expires
            # Returns: (queue_name, value) tuple, or None on timeout
            result = await r.blpop(self.queue_name, timeout=timeout)
            if result:
                return json.loads(result[1])  # result[1] is the actual value
        else:
            # LPOP returns the value immediately, or None if queue is empty
            result = await r.lpop(self.queue_name)
            if result:
                return json.loads(result)
        return None

    async def length(self) -> int:
        """Get the number of tasks in the queue."""
        r = await get_redis()
        return await r.llen(self.queue_name)


# Pre-configured instances
cache = RedisCache()
session_store = SessionStore()
task_queue = TaskQueue()
