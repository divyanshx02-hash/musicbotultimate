from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, Message

from helpers.decorators import anti_flood, is_admin
from strings.buttons import vote_skip_keyboard
from strings.messages import VOTE_SKIP_ALREADY, VOTE_SKIP_DONE, VOTE_SKIP_POLL


@Client.on_message(filters.command("voteskip") & (filters.group | filters.channel))
@anti_flood
async def voteskip_command(client: Client, message: Message):
    from bot import cache
    if not await cache.is_stream_active(message.chat.id):
        await message.reply("<b>No song is playing.</b>")
        return
    await _start_voteskip_from_message(client, message)


async def _start_voteskip_from_message(client: Client, message: Message):
    from bot import cache, db
    chat_id = message.chat.id
    threshold = await db.get_vote_skip_threshold(chat_id)
    await cache.clear_vote_skip(chat_id)
    kb = vote_skip_keyboard(chat_id, 0, 0)
    await message.reply(VOTE_SKIP_POLL.format(needed=threshold), reply_markup=kb)


async def _start_voteskip(client: Client, query: CallbackQuery, chat_id: int):
    from bot import cache, db
    if not await cache.is_stream_active(chat_id):
        await query.answer("No song is playing.", show_alert=True)
        return
    threshold = await db.get_vote_skip_threshold(chat_id)
    await cache.clear_vote_skip(chat_id)
    kb = vote_skip_keyboard(chat_id, 0, 0)
    await query.message.reply(VOTE_SKIP_POLL.format(needed=threshold), reply_markup=kb)
    await query.answer()


@Client.on_message(filters.command("setvoteskip") & (filters.group | filters.channel))
@is_admin
async def setvoteskip_command(client: Client, message: Message):
    from bot import db
    args = message.command
    if len(args) < 2 or not args[1].isdigit():
        current = await db.get_vote_skip_threshold(message.chat.id)
        await message.reply(f"<b>Current vote skip threshold:</b> {current}\nUsage: <code>/setvoteskip [number]</code>")
        return
    threshold = max(1, min(20, int(args[1])))
    await db.set_vote_skip_threshold(message.chat.id, threshold)
    await message.reply(f"<b>Vote skip threshold set to {threshold} votes.</b>")


@Client.on_message(filters.command("top10") & (filters.group | filters.channel))
async def top10_command(client: Client, message: Message):
    from bot import db
    songs = await db.get_top_songs(message.chat.id, limit=10)
    if not songs:
        await message.reply("<b>No song ratings yet. Like songs with the 👍 button!</b>")
        return
    lines = ["<b>Top 10 Most Liked Songs</b>\n"]
    for i, s in enumerate(songs, 1):
        lines.append(f"{i}. <code>{s.get('_id', 'Unknown')[:40]}</code> — 👍 {s.get('likes', 0)}")
    await message.reply("\n".join(lines))


@Client.on_message(filters.command("flop10") & (filters.group | filters.channel))
async def flop10_command(client: Client, message: Message):
    from bot import db
    songs = await db.get_flop_songs(message.chat.id, limit=10)
    if not songs:
        await message.reply("<b>No disliked songs yet.</b>")
        return
    lines = ["<b>Top 10 Most Disliked Songs</b>\n"]
    for i, s in enumerate(songs, 1):
        lines.append(f"{i}. <code>{s.get('_id', 'Unknown')[:40]}</code> — 👎 {s.get('dislikes', 0)}")
    await message.reply("\n".join(lines))
