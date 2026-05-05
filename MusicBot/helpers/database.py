import os
from datetime import datetime, timezone
from typing import Any, Optional

from loguru import logger

from config import HISTORY_LIMIT

# Supabase REST API client — no extra deps needed
SUPABASE_URL = os.getenv("SUPABASE_URL", os.getenv("VITE_SUPABASE_URL", ""))
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY", os.getenv("SUPABASE_ANON_KEY", os.getenv("VITE_SUPABASE_ANON_KEY", "")))


class Database:
    """Supabase REST API backend for MusicBot."""

    def __init__(self):
        import aiohttp
        self._session: Optional[aiohttp.ClientSession] = None
        self._url = SUPABASE_URL
        self._key = SUPABASE_KEY
        self._headers = {
            "apikey": self._key,
            "Authorization": f"Bearer {self._key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }

    async def connect(self):
        import aiohttp
        self._session = aiohttp.ClientSession()
        # Verify connection
        resp = await self._session.get(
            f"{self._url}/rest/v1/users?select=id&limit=1",
            headers=self._headers,
        )
        if resp.status in (200, 401):
            logger.info("Supabase database connected")
        else:
            text = await resp.text()
            raise RuntimeError(f"Supabase connection failed: {resp.status} {text}")

    async def close(self):
        if self._session:
            await self._session.close()

    async def _select(self, table: str, query: str = "", single: bool = False) -> Any:
        url = f"{self._url}/rest/v1/{table}?{query}"
        resp = await self._session.get(url, headers=self._headers)
        data = await resp.json()
        if resp.status >= 400:
            logger.error(f"DB select error {table}: {data}")
            return None
        if single:
            return data[0] if data else None
        return data

    async def _insert(self, table: str, payload: dict) -> Any:
        url = f"{self._url}/rest/v1/{table}"
        resp = await self._session.post(url, headers=self._headers, json=payload)
        data = await resp.json()
        if resp.status >= 400:
            logger.error(f"DB insert error {table}: {data}")
            return None
        return data

    async def _upsert(self, table: str, payload: dict, on_conflict: str = "") -> Any:
        url = f"{self._url}/rest/v1/{table}"
        headers = {**self._headers, "Prefer": "resolution=merge-duplicates,return=representation"}
        if on_conflict:
            url += f"?on_conflict={on_conflict}"
        resp = await self._session.post(url, headers=headers, json=payload)
        data = await resp.json()
        if resp.status >= 400:
            logger.error(f"DB upsert error {table}: {data}")
            return None
        return data

    async def _update(self, table: str, query: str, payload: dict) -> Any:
        url = f"{self._url}/rest/v1/{table}?{query}"
        headers = {**self._headers, "Prefer": "return=representation"}
        resp = await self._session.patch(url, headers=headers, json=payload)
        data = await resp.json()
        if resp.status >= 400:
            logger.error(f"DB update error {table}: {data}")
            return None
        return data

    async def _delete(self, table: str, query: str) -> Any:
        url = f"{self._url}/rest/v1/{table}?{query}"
        headers = {**self._headers, "Prefer": "return=representation"}
        resp = await self._session.delete(url, headers=headers)
        data = await resp.json()
        if resp.status >= 400:
            logger.error(f"DB delete error {table}: {data}")
            return None
        return data

    async def _rpc(self, fn: str, params: dict = None) -> Any:
        url = f"{self._url}/rest/v1/rpc/{fn}"
        resp = await self._session.post(url, headers=self._headers, json=params or {})
        data = await resp.json()
        if resp.status >= 400:
            logger.error(f"DB rpc error {fn}: {data}")
            return None
        return data

    # ── User management ──────────────────────────────────────────────

    async def get_user(self, user_id: int) -> Optional[dict]:
        return await self._select("users", f"user_id=eq.{user_id}", single=True)

    async def upsert_user(self, user_id: int, data: dict):
        payload = {"user_id": user_id, **data}
        await self._upsert("users", payload, on_conflict="user_id")

    async def get_all_users(self) -> list[dict]:
        return await self._select("users", "select=*") or []

    async def is_sudo(self, user_id: int) -> bool:
        from config import OWNER_ID
        if user_id in OWNER_ID:
            return True
        user = await self.get_user(user_id)
        return bool(user and user.get("sudo"))

    async def add_sudo(self, user_id: int):
        await self.upsert_user(user_id, {"sudo": True})

    async def remove_sudo(self, user_id: int):
        await self._update("users", f"user_id=eq.{user_id}", {"sudo": False})

    async def is_blocked(self, user_id: int) -> bool:
        user = await self.get_user(user_id)
        return bool(user and user.get("blocked"))

    async def block_user(self, user_id: int):
        await self.upsert_user(user_id, {"blocked": True})

    async def unblock_user(self, user_id: int):
        await self.upsert_user(user_id, {"blocked": False})

    # ── Chat management ───────────────────────────────────────────────

    async def get_chat(self, chat_id: int) -> Optional[dict]:
        return await self._select("chats", f"chat_id=eq.{chat_id}", single=True)

    async def upsert_chat(self, chat_id: int, data: dict):
        payload = {"chat_id": chat_id, **data}
        await self._upsert("chats", payload, on_conflict="chat_id")

    async def get_all_chats(self) -> list[dict]:
        return await self._select("chats", "select=*") or []

    async def is_chat_allowed(self, chat_id: int) -> bool:
        from config import PRIVATE_BOT_MODE, OWNER_ID
        if not PRIVATE_BOT_MODE:
            return True
        chat = await self.get_chat(chat_id)
        return bool(chat and chat.get("allowed"))

    async def allow_chat(self, chat_id: int):
        await self.upsert_chat(chat_id, {"allowed": True})

    async def disallow_chat(self, chat_id: int):
        await self.upsert_chat(chat_id, {"allowed": False})

    async def get_chat_lang(self, chat_id: int) -> str:
        chat = await self.get_chat(chat_id)
        return chat.get("lang", "en") if chat else "en"

    async def set_chat_lang(self, chat_id: int, lang: str):
        await self.upsert_chat(chat_id, {"lang": lang})

    async def get_chat_timezone(self, chat_id: int) -> str:
        chat = await self.get_chat(chat_id)
        return chat.get("timezone", "UTC") if chat else "UTC"

    async def set_chat_timezone(self, chat_id: int, tz: str):
        await self.upsert_chat(chat_id, {"timezone": tz})

    async def get_welcome(self, chat_id: int) -> Optional[str]:
        chat = await self.get_chat(chat_id)
        return chat.get("welcome") if chat else None

    async def set_welcome(self, chat_id: int, text: str):
        await self.upsert_chat(chat_id, {"welcome": text})

    async def get_rules(self, chat_id: int) -> Optional[str]:
        chat = await self.get_chat(chat_id)
        return chat.get("rules") if chat else None

    async def set_rules(self, chat_id: int, text: str):
        await self.upsert_chat(chat_id, {"rules": text})

    async def get_vote_skip_threshold(self, chat_id: int) -> int:
        chat = await self.get_chat(chat_id)
        return chat.get("vote_skip_threshold", 3) if chat else 3

    async def set_vote_skip_threshold(self, chat_id: int, threshold: int):
        await self.upsert_chat(chat_id, {"vote_skip_threshold": threshold})

    async def is_open_queue(self, chat_id: int) -> bool:
        chat = await self.get_chat(chat_id)
        return bool(chat and chat.get("open_queue", True))

    async def toggle_open_queue(self, chat_id: int):
        chat = await self.get_chat(chat_id)
        current = chat.get("open_queue", True) if chat else True
        await self.upsert_chat(chat_id, {"open_queue": not current})
        return not current

    async def is_247_mode(self, chat_id: int) -> bool:
        chat = await self.get_chat(chat_id)
        return bool(chat and chat.get("mode_247"))

    async def toggle_247(self, chat_id: int):
        chat = await self.get_chat(chat_id)
        current = chat.get("mode_247", False) if chat else False
        await self.upsert_chat(chat_id, {"mode_247": not current})
        return not current

    # ── Listening history ─────────────────────────────────────────────

    async def add_to_history(self, user_id: int, track: dict):
        payload = {
            "user_id": user_id,
            "chat_id": track.get("chat_id", 0),
            "title": track.get("title", ""),
            "artist": track.get("artist", ""),
            "video_id": track.get("video_id", ""),
            "platform": track.get("platform", ""),
            "played_at": datetime.now(timezone.utc).isoformat(),
        }
        await self._insert("history", payload)

    async def get_history(self, user_id: int, limit: int = 20) -> list[dict]:
        return await self._select("history", f"user_id=eq.{user_id}&order=played_at.desc&limit={limit}") or []

    async def get_chat_history(self, chat_id: int, limit: int = 50) -> list[dict]:
        return await self._select("history", f"chat_id=eq.{chat_id}&order=played_at.desc&limit={limit}") or []

    # ── Song ratings ──────────────────────────────────────────────────

    async def rate_song(self, chat_id: int, video_id: str, user_id: int, vote: int):
        payload = {
            "chat_id": chat_id,
            "video_id": video_id,
            "user_id": user_id,
            "vote": vote,
            "rated_at": datetime.now(timezone.utc).isoformat(),
        }
        await self._upsert("song_ratings", payload, on_conflict="chat_id,video_id,user_id")

    async def get_song_score(self, chat_id: int, video_id: str) -> dict:
        likes_data = await self._select("song_ratings", f"chat_id=eq.{chat_id}&video_id=eq.{video_id}&vote=eq.1&select=id") or []
        dislikes_data = await self._select("song_ratings", f"chat_id=eq.{chat_id}&video_id=eq.{video_id}&vote=eq.-1&select=id") or []
        return {"likes": len(likes_data), "dislikes": len(dislikes_data)}

    async def get_top_songs(self, chat_id: int, limit: int = 10) -> list[dict]:
        # Use RPC for aggregation
        return await self._rpc("get_top_songs", {"chat_id": chat_id, "limit": limit}) or []

    async def get_flop_songs(self, chat_id: int, limit: int = 10) -> list[dict]:
        return await self._rpc("get_flop_songs", {"chat_id": chat_id, "limit": limit}) or []

    # ── Favourites ────────────────────────────────────────────────────

    async def add_favourite(self, user_id: int, track: dict):
        payload = {
            "user_id": user_id,
            "video_id": track.get("video_id", ""),
            "title": track.get("title", ""),
            "artist": track.get("artist", ""),
            "url": track.get("url", ""),
            "thumbnail": track.get("thumbnail"),
            "platform": track.get("platform", ""),
            "saved_at": datetime.now(timezone.utc).isoformat(),
        }
        await self._upsert("favourites", payload, on_conflict="user_id,video_id")

    async def remove_favourite(self, user_id: int, video_id: str):
        await self._delete("favourites", f"user_id=eq.{user_id}&video_id=eq.{video_id}")

    async def get_favourites(self, user_id: int) -> list[dict]:
        return await self._select("favourites", f"user_id=eq.{user_id}&order=saved_at.desc") or []

    async def is_favourite(self, user_id: int, video_id: str) -> bool:
        result = await self._select("favourites", f"user_id=eq.{user_id}&video_id=eq.{video_id}&select=id", single=True)
        return result is not None

    # ── Quiz scores ───────────────────────────────────────────────────

    async def add_quiz_point(self, chat_id: int, user_id: int, username: str):
        payload = {"chat_id": chat_id, "user_id": user_id, "username": username, "points": 1}
        # Use upsert with increment via RPC or manual approach
        existing = await self._select("quiz_scores", f"chat_id=eq.{chat_id}&user_id=eq.{user_id}", single=True)
        if existing:
            await self._update("quiz_scores", f"chat_id=eq.{chat_id}&user_id=eq.{user_id}", {
                "points": (existing.get("points", 0) + 1),
                "username": username,
            })
        else:
            await self._insert("quiz_scores", payload)

    async def get_quiz_leaderboard(self, chat_id: int, limit: int = 10) -> list[dict]:
        return await self._select("quiz_scores", f"chat_id=eq.{chat_id}&order=points.desc&limit={limit}") or []

    async def get_global_quiz_leaderboard(self, limit: int = 10) -> list[dict]:
        return await self._rpc("get_global_quiz_leaderboard", {"limit": limit}) or []

    # ── Global ban ────────────────────────────────────────────────────

    async def gban_user(self, user_id: int, reason: str = ""):
        payload = {"user_id": user_id, "reason": reason, "banned_at": datetime.now(timezone.utc).isoformat()}
        await self._upsert("gban", payload, on_conflict="user_id")

    async def ungban_user(self, user_id: int):
        await self._delete("gban", f"user_id=eq.{user_id}")

    async def is_gbanned(self, user_id: int) -> bool:
        result = await self._select("gban", f"user_id=eq.{user_id}&select=id", single=True)
        return result is not None

    # ── Warnings ──────────────────────────────────────────────────────

    async def add_warn(self, chat_id: int, user_id: int, reason: str = "") -> int:
        import json
        existing = await self._select("warned", f"chat_id=eq.{chat_id}&user_id=eq.{user_id}", single=True)
        if existing:
            warnings = existing.get("warnings", [])
            if isinstance(warnings, str):
                warnings = json.loads(warnings)
            warnings.append({"reason": reason, "at": datetime.now(timezone.utc).isoformat()})
            await self._update("warned", f"chat_id=eq.{chat_id}&user_id=eq.{user_id}", {"warnings": warnings})
            return len(warnings)
        else:
            warnings = [{"reason": reason, "at": datetime.now(timezone.utc).isoformat()}]
            await self._insert("warned", {"chat_id": chat_id, "user_id": user_id, "warnings": warnings})
            return 1

    async def get_warns(self, chat_id: int, user_id: int) -> list:
        import json
        doc = await self._select("warned", f"chat_id=eq.{chat_id}&user_id=eq.{user_id}", single=True)
        if not doc:
            return []
        warnings = doc.get("warnings", [])
        if isinstance(warnings, str):
            warnings = json.loads(warnings)
        return warnings

    async def reset_warns(self, chat_id: int, user_id: int):
        await self._update("warned", f"chat_id=eq.{chat_id}&user_id=eq.{user_id}", {"warnings": []})

    # ── Radio stations ────────────────────────────────────────────────

    async def get_radio_stations(self) -> list[dict]:
        return await self._select("radio_stations", "select=*") or []

    async def add_radio_station(self, data: dict):
        await self._upsert("radio_stations", data, on_conflict="name")

    async def remove_radio_station(self, name: str):
        await self._delete("radio_stations", f"name=eq.{name}")

    # ── Schedules ─────────────────────────────────────────────────────

    async def add_schedule(self, data: dict) -> str:
        result = await self._insert("schedules", data)
        return result[0]["id"] if result else ""

    async def get_schedules(self, chat_id: int) -> list[dict]:
        return await self._select("schedules", f"chat_id=eq.{chat_id}&order=run_at") or []

    async def delete_schedule(self, schedule_id: str):
        await self._delete("schedules", f"id=eq.{schedule_id}")

    async def clear_schedules(self, chat_id: int):
        await self._delete("schedules", f"chat_id=eq.{chat_id}")

    # ── Bot stats ─────────────────────────────────────────────────────

    async def get_stats(self) -> dict:
        users = await self._select("users", "select=id") or []
        chats = await self._select("chats", "select=id") or []
        history = await self._select("history", "select=id") or []
        sudo_users = await self._select("users", "sudo=eq.true&select=id") or []
        return {
            "users": len(users),
            "chats": len(chats),
            "songs_played": len(history),
            "sudo_users": len(sudo_users),
        }

    # ── Wrapped stats ─────────────────────────────────────────────────

    async def get_user_wrapped(self, user_id: int, year: int) -> dict:
        start = f"{year}-01-01T00:00:00+00:00"
        end = f"{year}-12-31T23:59:59+00:00"
        entries = await self._select(
            "history",
            f"user_id=eq.{user_id}&played_at=gte.{start}&played_at=lte.{end}&select=title,artist,played_at"
        ) or []
        return self._compute_wrapped(entries)

    async def get_chat_wrapped(self, chat_id: int, year: int) -> dict:
        start = f"{year}-01-01T00:00:00+00:00"
        end = f"{year}-12-31T23:59:59+00:00"
        entries = await self._select(
            "history",
            f"chat_id=eq.{chat_id}&played_at=gte.{start}&played_at=lte.{end}&select=title,artist,played_at"
        ) or []
        return self._compute_wrapped(entries)

    def _compute_wrapped(self, entries: list[dict]) -> dict:
        from collections import Counter
        if not entries:
            return {}
        song_counts = Counter(e.get("title", "Unknown") for e in entries)
        artist_counts = Counter(e.get("artist", "Unknown") for e in entries)
        hour_counts = Counter(
            int(e["played_at"][:13].split("T")[1][:2]) if "played_at" in e and e["played_at"] else 0
            for e in entries
        )
        peak_hour = hour_counts.most_common(1)[0][0] if hour_counts else 0
        top_song = song_counts.most_common(1)[0] if song_counts else ("Unknown", 0)
        top_artist = artist_counts.most_common(1)[0] if artist_counts else ("Unknown", 0)
        return {
            "total_songs": len(entries),
            "top_song": top_song[0],
            "top_song_count": top_song[1],
            "top_artist": top_artist[0],
            "top_artist_count": top_artist[1],
            "peak_hour": peak_hour,
            "hour_data": dict(hour_counts),
        }
