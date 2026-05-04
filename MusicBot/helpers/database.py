from datetime import datetime, timezone
from typing import Any, Optional

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from loguru import logger

from config import MONGO_DB_URI, HISTORY_LIMIT


class Database:
    def __init__(self):
        self.client: Optional[AsyncIOMotorClient] = None
        self.db: Optional[AsyncIOMotorDatabase] = None

    async def connect(self):
        self.client = AsyncIOMotorClient(MONGO_DB_URI)
        self.db = self.client["musicbot"]
        await self.db.command("ping")
        await self._create_indexes()
        logger.info("MongoDB connected and indexes created")

    async def close(self):
        if self.client:
            self.client.close()

    async def _create_indexes(self):
        await self.db.users.create_index("user_id", unique=True)
        await self.db.chats.create_index("chat_id", unique=True)
        await self.db.history.create_index([("user_id", 1), ("played_at", -1)])
        await self.db.song_ratings.create_index([("chat_id", 1), ("video_id", 1)])
        await self.db.quiz_scores.create_index([("chat_id", 1), ("user_id", 1)])
        await self.db.favourites.create_index([("user_id", 1), ("video_id", 1)])
        await self.db.radio_stations.create_index("name", unique=True)
        await self.db.schedules.create_index([("chat_id", 1), ("run_at", 1)])
        await self.db.gban.create_index("user_id", unique=True)
        await self.db.warned.create_index([("chat_id", 1), ("user_id", 1)])

    # ── User management ──────────────────────────────────────────────

    async def get_user(self, user_id: int) -> Optional[dict]:
        return await self.db.users.find_one({"user_id": user_id})

    async def upsert_user(self, user_id: int, data: dict):
        await self.db.users.update_one(
            {"user_id": user_id},
            {"$set": data, "$setOnInsert": {"user_id": user_id, "joined": datetime.now(timezone.utc)}},
            upsert=True,
        )

    async def get_all_users(self) -> list[dict]:
        return await self.db.users.find({}).to_list(length=None)

    async def is_sudo(self, user_id: int) -> bool:
        from config import OWNER_ID
        if user_id in OWNER_ID:
            return True
        user = await self.get_user(user_id)
        return bool(user and user.get("sudo"))

    async def add_sudo(self, user_id: int):
        await self.upsert_user(user_id, {"sudo": True})

    async def remove_sudo(self, user_id: int):
        await self.db.users.update_one({"user_id": user_id}, {"$set": {"sudo": False}})

    async def is_blocked(self, user_id: int) -> bool:
        user = await self.get_user(user_id)
        return bool(user and user.get("blocked"))

    async def block_user(self, user_id: int):
        await self.upsert_user(user_id, {"blocked": True})

    async def unblock_user(self, user_id: int):
        await self.upsert_user(user_id, {"blocked": False})

    # ── Chat management ───────────────────────────────────────────────

    async def get_chat(self, chat_id: int) -> Optional[dict]:
        return await self.db.chats.find_one({"chat_id": chat_id})

    async def upsert_chat(self, chat_id: int, data: dict):
        await self.db.chats.update_one(
            {"chat_id": chat_id},
            {"$set": data, "$setOnInsert": {"chat_id": chat_id}},
            upsert=True,
        )

    async def get_all_chats(self) -> list[dict]:
        return await self.db.chats.find({}).to_list(length=None)

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
        track["user_id"] = user_id
        track["played_at"] = datetime.now(timezone.utc)
        await self.db.history.insert_one(track)
        # Keep only last HISTORY_LIMIT entries
        count = await self.db.history.count_documents({"user_id": user_id})
        if count > HISTORY_LIMIT:
            oldest = await self.db.history.find({"user_id": user_id}).sort("played_at", 1).limit(count - HISTORY_LIMIT).to_list(length=None)
            ids = [d["_id"] for d in oldest]
            await self.db.history.delete_many({"_id": {"$in": ids}})

    async def get_history(self, user_id: int, limit: int = 20) -> list[dict]:
        return await self.db.history.find({"user_id": user_id}).sort("played_at", -1).limit(limit).to_list(length=None)

    async def get_chat_history(self, chat_id: int, limit: int = 50) -> list[dict]:
        return await self.db.history.find({"chat_id": chat_id}).sort("played_at", -1).limit(limit).to_list(length=None)

    # ── Song ratings ──────────────────────────────────────────────────

    async def rate_song(self, chat_id: int, video_id: str, user_id: int, vote: int):
        await self.db.song_ratings.update_one(
            {"chat_id": chat_id, "video_id": video_id, "user_id": user_id},
            {"$set": {"vote": vote, "rated_at": datetime.now(timezone.utc)}},
            upsert=True,
        )

    async def get_song_score(self, chat_id: int, video_id: str) -> dict:
        likes = await self.db.song_ratings.count_documents({"chat_id": chat_id, "video_id": video_id, "vote": 1})
        dislikes = await self.db.song_ratings.count_documents({"chat_id": chat_id, "video_id": video_id, "vote": -1})
        return {"likes": likes, "dislikes": dislikes}

    async def get_top_songs(self, chat_id: int, limit: int = 10) -> list[dict]:
        pipeline = [
            {"$match": {"chat_id": chat_id, "vote": 1}},
            {"$group": {"_id": "$video_id", "likes": {"$sum": 1}}},
            {"$sort": {"likes": -1}},
            {"$limit": limit},
        ]
        return await self.db.song_ratings.aggregate(pipeline).to_list(length=None)

    async def get_flop_songs(self, chat_id: int, limit: int = 10) -> list[dict]:
        pipeline = [
            {"$match": {"chat_id": chat_id, "vote": -1}},
            {"$group": {"_id": "$video_id", "dislikes": {"$sum": 1}}},
            {"$sort": {"dislikes": -1}},
            {"$limit": limit},
        ]
        return await self.db.song_ratings.aggregate(pipeline).to_list(length=None)

    # ── Favourites ────────────────────────────────────────────────────

    async def add_favourite(self, user_id: int, track: dict):
        track["user_id"] = user_id
        track["saved_at"] = datetime.now(timezone.utc)
        await self.db.favourites.update_one(
            {"user_id": user_id, "video_id": track.get("video_id")},
            {"$set": track},
            upsert=True,
        )

    async def remove_favourite(self, user_id: int, video_id: str):
        await self.db.favourites.delete_one({"user_id": user_id, "video_id": video_id})

    async def get_favourites(self, user_id: int) -> list[dict]:
        return await self.db.favourites.find({"user_id": user_id}).sort("saved_at", -1).to_list(length=None)

    async def is_favourite(self, user_id: int, video_id: str) -> bool:
        doc = await self.db.favourites.find_one({"user_id": user_id, "video_id": video_id})
        return doc is not None

    # ── Quiz scores ───────────────────────────────────────────────────

    async def add_quiz_point(self, chat_id: int, user_id: int, username: str):
        await self.db.quiz_scores.update_one(
            {"chat_id": chat_id, "user_id": user_id},
            {"$inc": {"points": 1}, "$set": {"username": username}},
            upsert=True,
        )

    async def get_quiz_leaderboard(self, chat_id: int, limit: int = 10) -> list[dict]:
        return await self.db.quiz_scores.find({"chat_id": chat_id}).sort("points", -1).limit(limit).to_list(length=None)

    async def get_global_quiz_leaderboard(self, limit: int = 10) -> list[dict]:
        pipeline = [
            {"$group": {"_id": "$user_id", "points": {"$sum": "$points"}, "username": {"$first": "$username"}}},
            {"$sort": {"points": -1}},
            {"$limit": limit},
        ]
        return await self.db.quiz_scores.aggregate(pipeline).to_list(length=None)

    # ── Global ban ────────────────────────────────────────────────────

    async def gban_user(self, user_id: int, reason: str = ""):
        await self.db.gban.update_one(
            {"user_id": user_id},
            {"$set": {"reason": reason, "banned_at": datetime.now(timezone.utc)}},
            upsert=True,
        )

    async def ungban_user(self, user_id: int):
        await self.db.gban.delete_one({"user_id": user_id})

    async def is_gbanned(self, user_id: int) -> bool:
        doc = await self.db.gban.find_one({"user_id": user_id})
        return doc is not None

    # ── Warnings ──────────────────────────────────────────────────────

    async def add_warn(self, chat_id: int, user_id: int, reason: str = "") -> int:
        result = await self.db.warned.find_one_and_update(
            {"chat_id": chat_id, "user_id": user_id},
            {"$push": {"warnings": {"reason": reason, "at": datetime.now(timezone.utc)}}},
            upsert=True,
            return_document=True,
        )
        return len(result.get("warnings", [])) if result else 1

    async def get_warns(self, chat_id: int, user_id: int) -> list:
        doc = await self.db.warned.find_one({"chat_id": chat_id, "user_id": user_id})
        return doc.get("warnings", []) if doc else []

    async def reset_warns(self, chat_id: int, user_id: int):
        await self.db.warned.update_one(
            {"chat_id": chat_id, "user_id": user_id},
            {"$set": {"warnings": []}},
        )

    # ── Radio stations ────────────────────────────────────────────────

    async def get_radio_stations(self) -> list[dict]:
        return await self.db.radio_stations.find({}).to_list(length=None)

    async def add_radio_station(self, data: dict):
        await self.db.radio_stations.update_one({"name": data["name"]}, {"$set": data}, upsert=True)

    async def remove_radio_station(self, name: str):
        await self.db.radio_stations.delete_one({"name": name})

    # ── Schedules ─────────────────────────────────────────────────────

    async def add_schedule(self, data: dict) -> str:
        result = await self.db.schedules.insert_one(data)
        return str(result.inserted_id)

    async def get_schedules(self, chat_id: int) -> list[dict]:
        return await self.db.schedules.find({"chat_id": chat_id}).to_list(length=None)

    async def delete_schedule(self, schedule_id: str):
        from bson import ObjectId
        await self.db.schedules.delete_one({"_id": ObjectId(schedule_id)})

    async def clear_schedules(self, chat_id: int):
        await self.db.schedules.delete_many({"chat_id": chat_id})

    # ── Bot stats ─────────────────────────────────────────────────────

    async def get_stats(self) -> dict:
        total_users = await self.db.users.count_documents({})
        total_chats = await self.db.chats.count_documents({})
        total_history = await self.db.history.count_documents({})
        sudo_users = await self.db.users.count_documents({"sudo": True})
        return {
            "users": total_users,
            "chats": total_chats,
            "songs_played": total_history,
            "sudo_users": sudo_users,
        }

    # ── Wrapped stats ─────────────────────────────────────────────────

    async def get_user_wrapped(self, user_id: int, year: int) -> dict:
        from datetime import date
        start = datetime(year, 1, 1, tzinfo=timezone.utc)
        end = datetime(year, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
        entries = await self.db.history.find(
            {"user_id": user_id, "played_at": {"$gte": start, "$lte": end}}
        ).to_list(length=None)
        return self._compute_wrapped(entries)

    async def get_chat_wrapped(self, chat_id: int, year: int) -> dict:
        start = datetime(year, 1, 1, tzinfo=timezone.utc)
        end = datetime(year, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
        entries = await self.db.history.find(
            {"chat_id": chat_id, "played_at": {"$gte": start, "$lte": end}}
        ).to_list(length=None)
        return self._compute_wrapped(entries)

    def _compute_wrapped(self, entries: list[dict]) -> dict:
        from collections import Counter
        if not entries:
            return {}
        song_counts = Counter(e.get("title", "Unknown") for e in entries)
        artist_counts = Counter(e.get("artist", "Unknown") for e in entries)
        hour_counts = Counter(e["played_at"].hour for e in entries if "played_at" in e)
        peak_hour = hour_counts.most_common(1)[0][0] if hour_counts else 0
        top_song = song_counts.most_common(1)[0] if song_counts else ("Unknown", 0)
        top_artist = artist_counts.most_common(1)[0] if artist_counts else ("Unknown", 0)
        dates = sorted(set(e["played_at"].date() for e in entries if "played_at" in e))
        streak = 0
        max_streak = 0
        for i, d in enumerate(dates):
            if i == 0:
                streak = 1
            else:
                from datetime import timedelta
                if dates[i] - dates[i - 1] == timedelta(days=1):
                    streak += 1
                else:
                    streak = 1
            max_streak = max(max_streak, streak)
        return {
            "total_songs": len(entries),
            "top_song": top_song[0],
            "top_song_count": top_song[1],
            "top_artist": top_artist[0],
            "top_artist_count": top_artist[1],
            "peak_hour": peak_hour,
            "streak": max_streak,
            "hour_data": dict(hour_counts),
        }
