import json
from typing import Any, Optional

import aioredis
from loguru import logger

from config import CACHE_TTL, REDIS_URL


class RedisCache:
    def __init__(self):
        self.redis: Optional[aioredis.Redis] = None

    async def connect(self):
        self.redis = await aioredis.from_url(REDIS_URL, decode_responses=True)
        await self.redis.ping()
        logger.info("Redis connected")

    async def close(self):
        if self.redis:
            await self.redis.close()

    # ── Generic helpers ───────────────────────────────────────────────

    async def get(self, key: str) -> Optional[Any]:
        val = await self.redis.get(key)
        if val is None:
            return None
        try:
            return json.loads(val)
        except (json.JSONDecodeError, TypeError):
            return val

    async def set(self, key: str, value: Any, ttl: int = CACHE_TTL):
        data = json.dumps(value) if not isinstance(value, str) else value
        await self.redis.set(key, data, ex=ttl)

    async def delete(self, key: str):
        await self.redis.delete(key)

    async def exists(self, key: str) -> bool:
        return bool(await self.redis.exists(key))

    async def expire(self, key: str, ttl: int):
        await self.redis.expire(key, ttl)

    # ── Queue management ──────────────────────────────────────────────

    def _queue_key(self, chat_id: int) -> str:
        return f"queue:{chat_id}"

    async def get_queue(self, chat_id: int) -> list[dict]:
        data = await self.redis.get(self._queue_key(chat_id))
        if not data:
            return []
        try:
            return json.loads(data)
        except Exception:
            return []

    async def set_queue(self, chat_id: int, queue: list[dict]):
        await self.redis.set(self._queue_key(chat_id), json.dumps(queue))

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
        await self.redis.delete(self._queue_key(chat_id))

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
        import random
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
        val = await self.redis.get(f"effect:{chat_id}")
        return val or "Normal"

    async def set_effect(self, chat_id: int, effect: str):
        await self.redis.set(f"effect:{chat_id}", effect)

    # ── Loop mode ─────────────────────────────────────────────────────

    async def get_loop(self, chat_id: int) -> str:
        val = await self.redis.get(f"loop:{chat_id}")
        return val or "off"  # off | one | all

    async def set_loop(self, chat_id: int, mode: str):
        await self.redis.set(f"loop:{chat_id}", mode)

    # ── Volume ────────────────────────────────────────────────────────

    async def get_volume(self, chat_id: int) -> int:
        val = await self.redis.get(f"volume:{chat_id}")
        return int(val) if val else 100

    async def set_volume(self, chat_id: int, volume: int):
        await self.redis.set(f"volume:{chat_id}", str(max(0, min(200, volume))))

    # ── Now playing message tracking ──────────────────────────────────

    async def set_np_message(self, chat_id: int, msg_id: int):
        await self.redis.set(f"npm:{chat_id}", str(msg_id))

    async def get_np_message(self, chat_id: int) -> Optional[int]:
        val = await self.redis.get(f"npm:{chat_id}")
        return int(val) if val else None

    # ── Assistant assignment ──────────────────────────────────────────

    async def get_assistant(self, chat_id: int) -> Optional[int]:
        val = await self.redis.get(f"assistant:{chat_id}")
        return int(val) if val else None

    async def set_assistant(self, chat_id: int, assistant_index: int):
        await self.redis.set(f"assistant:{chat_id}", str(assistant_index))

    # ── Stream state ──────────────────────────────────────────────────

    async def set_stream_active(self, chat_id: int, active: bool):
        await self.redis.set(f"stream:{chat_id}", "1" if active else "0")

    async def is_stream_active(self, chat_id: int) -> bool:
        val = await self.redis.get(f"stream:{chat_id}")
        return val == "1"

    # ── File ID cache ─────────────────────────────────────────────────

    async def get_file_id(self, video_id: str) -> Optional[str]:
        return await self.redis.get(f"fid:{video_id}")

    async def set_file_id(self, video_id: str, file_id: str):
        await self.redis.set(f"fid:{video_id}", file_id, ex=CACHE_TTL)

    # ── Anti-flood ────────────────────────────────────────────────────

    async def check_flood(self, user_id: int, window: float = 0.5) -> bool:
        key = f"flood:{user_id}"
        if await self.redis.exists(key):
            return True
        await self.redis.set(key, "1", px=int(window * 1000))
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
        await self.redis.sadd(key, str(user_id))
        await self.redis.expire(key, 60)
        return await self.redis.scard(key)

    async def clear_vote_skip(self, chat_id: int):
        await self.redis.delete(f"voteskip:{chat_id}")

    async def get_vote_skip_count(self, chat_id: int) -> int:
        return await self.redis.scard(f"voteskip:{chat_id}")

    # ── Ping ─────────────────────────────────────────────────────────

    async def ping(self) -> float:
        import time
        start = time.monotonic()
        await self.redis.ping()
        return (time.monotonic() - start) * 1000
