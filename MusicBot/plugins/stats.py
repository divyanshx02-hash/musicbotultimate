import time

from pyrogram import Client, filters
from pyrogram.types import Message

from helpers.decorators import is_owner
from helpers.utils import get_readable_time


_start_time = time.time()


@Client.on_message(filters.command("stats") & (filters.group | filters.private))
@is_owner
async def stats_command(client: Client, message: Message):
    from bot import assistant_manager, db
    stats = await db.get_stats()
    uptime = int(time.time() - _start_time)
    active = len([a for a in assistant_manager.assistants if a.available])

    from strings.messages import BOT_STATS
    await message.reply(BOT_STATS.format(
        users=stats.get("users", 0),
        chats=stats.get("chats", 0),
        songs_played=stats.get("songs_played", 0),
        sudo_users=stats.get("sudo_users", 0),
        uptime=get_readable_time(uptime),
        assistants=f"{active}/{len(assistant_manager.assistants)}",
    ))


@Client.on_message(filters.command("dbstats") & (filters.group | filters.private))
@is_owner
async def dbstats_command(client: Client, message: Message):
    from bot import db
    collections = ["users", "chats", "history", "favourites", "quiz_scores", "song_ratings", "radio_stations"]
    lines = ["<b>Database Stats</b>\n"]
    for col in collections:
        count = await db.db[col].count_documents({})
        lines.append(f"<b>{col}:</b> {count} documents")
    await message.reply("\n".join(lines))
