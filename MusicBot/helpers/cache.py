import json
import random
import time
from typing import Any, Optional

from loguru import logger

from config import CACHE_TTL, REDIS_URL

# Try Redis, fall back to in-memory
_redis_available = False
try:
    import aioredis
    _redis_available = True
except ImportError:
    pass


class _MemoryStore:
    """In-memory fallback when Redis is unavailable."""

    def __init__(self):
        self._data: dict[str, tuple[Any, float]] = {}  # key -> (value, expires_at)
        self._sets: dict[str, set[str]] = {}

    def _cleanup(self):
        now = time.monotonic()
        expired = [k for k, (_, exp) in self._data.items() if exp > 0 and exp < now]
        for k in expired:
            del self._data[k]

    async def get(self, key: str) -> Optional[str]:
        self._cleanup()
        if key in self._data:
            val, exp = self._data[key]
            if exp > 0 and exp < time.monotonic():
                del self._data[key]
                return None
            return val
        return None

    async def set(self, key: str, value: str, ex: int = 0, px: int = 0):
        ttl = 0
        if ex:
            ttl = time.monotonic() + ex
        elif px:
            ttl = time.monotonic() + px / 1000
        self._data[key] = (value, ttl)

    async def delete(self, key: str):
        self._data.pop(key, None)
        self._sets.pop(key, None)

    async def exists(self, key: str) -> bool:
        self._cleanup()
        return key in self._data

    async def expire(self, key: str, ttl: int):
        if key in self._data:
            val, _ = self._data[key]
            self._data[key] = (val, time.monotonic() + ttl)

    async def sadd(self, key: str, *members: str):
        if key not in self._sets:
            self._sets[key] = set()
        self._sets[key].update(members)

    async def scard(self, key: str) -> int:
        return len(self._sets.get(key, set()))

    async def ping(self) -> bool:
        return True

    async def close(self):
        self._data.clear()
        self._sets.clear()


class RedisCache:
    def __init__(self):
        self.redis = None
        self._memory = _MemoryStore()
        self._use_memory = False

    async def connect(self):
        global _redis_available
        if not _redis_available:
            logger.warning("aioredis not installed — using in-memory cache")
            self._use_memory = True
            return

        try:
            self.redis = await aioredis.from_url(REDIS_URL, decode_responses=True)
            await self.redis.ping()
            logger.info("Redis connected")
        except Exception as e:
            logger.warning(f"Redis connection failed: {e} — using in-memory cache")
            self._use_memory = True

    async def close(self):
        if self.redis and not self._use_memory:
            await self.redis.close()
        else:
            await self._memory.close()

    def _store(self):
        return self._memory if self._use_memory else self.redis

    # ── Generic helpers ───────────────────────────────────────────────

    async def get(self, key: str) -> Optional[Any]:
        store = self._store()
        val = await store.get(key)
        if val is None:
            return None
        try:
            return json.loads(val)
        except (json.JSONDecodeError, TypeError):
            return val

    async def set(self, key: str, value: Any, ttl: int = CACHE_TTL):
        data = json.dumps(value) if not isinstance(value, str) else value
        store = self._store()
        await store.set(key, data, ex=ttl)

    async def delete(self, key: str):
        await self._store().delete(key)

    async def exists(self, key: str) -> bool:
        return bool(await self._store().exists(key))

    async def expire(self, key: str, ttl: int):
        await self._store().expire(key, ttl)

    # ── Queue management ──────────────────────────────────────────────

    def _queue_key(self, chat_id: int) -> str:
        return f"queue:{chat_id}"

    async def get_queue(self, chat_id: int) -> list[dict]:
        store = self._store()
        data = await store.get(self._queue_key(chat_id))
        if not data:
            return []
        try:
            return json.loads(data)
        except Exception:
            return []

    async def set_queue(self, chat_id: int, queue: list[dict]):
        store = self._store()
        await store.set(self._queue_key(chat_id), json.dumps(queue))

    async def add_to_queue(self, chat_id: int, track: dict) -> int:
        queue = await self.get_queue(chat_id)
        queue.append(track)
        await self.set_queue(chat_id, queue)
        return len(queue)

    async def pop_queue(self, chat_id: int) -> Optional[dict]:
        queue = await self.get_queue(chat_id)
        if not queue:
            return None
        track = queue.pop(0)
        await self.set_queue(chat_id, queue)
        return track

    async def clear_queue(self, chat_id: int):
        await self._store().delete(self._queue_key(chat_id))

    async def remove_from_queue(self, chat_id: int, index: int) -> bool:
        queue = await self.get_queue(chat_id)
        if index < 0 or index >= len(queue):
            return False
        queue.pop(index)
        await self.set_queue(chat_id, queue)
        return True

    async def move_in_queue(self, chat_id: int, from_idx: int, to_idx: int) -> bool:
        queue = await self.get_queue(chat_id)
        if from_idx < 0 or from_idx >= len(queue) or to_idx < 0 or to_idx >= len(queue):
            return False
        item = queue.pop(from_idx)
        queue.insert(to_idx, item)
        await self.set_queue(chat_id, queue)
        return True

    async def shuffle_queue(self, chat_id: int):
        queue = await self.get_queue(chat_id)
        if len(queue) > 1:
            random.shuffle(queue)
        await self.set_queue(chat_id, queue)

    # ── Now playing ───────────────────────────────────────────────────

    def _np_key(self, chat_id: int) -> str:
        return f"np:{chat_id}"

    async def get_now_playing(self, chat_id: int) -> Optional[dict]:
        return await self.get(self._np_key(chat_id))

    async def set_now_playing(self, chat_id: int, track: dict):
        await self.set(self._np_key(chat_id), track, ttl=86400)

    async def clear_now_playing(self, chat_id: int):
        await self.delete(self._np_key(chat_id))

    # ── Active effect per chat ────────────────────────────────────────

    async def get_effect(self, chat_id: int) -> str:
        val = await self._store().get(f"effect:{chat_id}")
        return val or "Normal"

    async def set_effect(self, chat_id: int, effect: str):
        await self._store().set(f"effect:{chat_id}", effect)

    # ── Loop mode ─────────────────────────────────────────────────────

    async def get_loop(self, chat_id: int) -> str:
        val = await self._store().get(f"loop:{chat_id}")
        return val or "off"

    async def set_loop(self, chat_id: int, mode: str):
        await self._store().set(f"loop:{chat_id}", mode)

    # ── Volume ────────────────────────────────────────────────────────

    async def get_volume(self, chat_id: int) -> int:
        val = await self._store().get(f"volume:{chat_id}")
        return int(val) if val else 100

    async def set_volume(self, chat_id: int, volume: int):
        await self._store().set(f"volume:{chat_id}", str(max(0, min(200, volume))))

    # ── Now playing message tracking ──────────────────────────────────

    async def set_np_message(self, chat_id: int, msg_id: int):
        await self._store().set(f"npm:{chat_id}", str(msg_id))

    async def get_np_message(self, chat_id: int) -> Optional[int]:
        val = await self._store().get(f"npm:{chat_id}")
        return int(val) if val else None

    # ── Assistant assignment ──────────────────────────────────────────

    async def get_assistant(self, chat_id: int) -> Optional[int]:
        val = await self._store().get(f"assistant:{chat_id}")
        return int(val) if val else None

    async def set_assistant(self, chat_id: int, assistant_index: int):
        await self._store().set(f"assistant:{chat_id}", str(assistant_index))

    # ── Stream state ──────────────────────────────────────────────────

    async def set_stream_active(self, chat_id: int, active: bool):
        await self._store().set(f"stream:{chat_id}", "1" if active else "0")

    async def is_stream_active(self, chat_id: int) -> bool:
        val = await self._store().get(f"stream:{chat_id}")
        return val == "1"

    # ── File ID cache ─────────────────────────────────────────────────

    async def get_file_id(self, video_id: str) -> Optional[str]:
        return await self._store().get(f"fid:{video_id}")

    async def set_file_id(self, video_id: str, file_id: str):
        await self._store().set(f"fid:{video_id}", file_id, ex=CACHE_TTL)

    # ── Anti-flood ────────────────────────────────────────────────────

    async def check_flood(self, user_id: int, window: float = 0.5) -> bool:
        key = f"flood:{user_id}"
        if await self._store().exists(key):
            return True
        await self._store().set(key, "1", px=int(window * 1000))
        return False

    # ── Quiz state ────────────────────────────────────────────────────

    async def set_quiz_state(self, chat_id: int, state: dict):
        await self.set(f"quiz:{chat_id}", state, ttl=3600)

    async def get_quiz_state(self, chat_id: int) -> Optional[dict]:
        return await self.get(f"quiz:{chat_id}")

    async def clear_quiz_state(self, chat_id: int):
        await self.delete(f"quiz:{chat_id}")

    # ── Vote skip ─────────────────────────────────────────────────────

    async def add_vote_skip(self, chat_id: int, user_id: int) -> int:
        key = f"voteskip:{chat_id}"
        store = self._store()
        await store.sadd(key, str(user_id))
        await store.expire(key, 60)
        return await store.scard(key)

    async def clear_vote_skip(self, chat_id: int):
        await self._store().delete(f"voteskip:{chat_id}")

    async def get_vote_skip_count(self, chat_id: int) -> int:
        return await self._store().scard(f"voteskip:{chat_id}")

    # ── Ping ─────────────────────────────────────────────────────────

    async def ping(self) -> float:
        start = time.monotonic()
        await self._store().ping()
        return (time.monotonic() - start) * 1000
