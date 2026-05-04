from pyrogram import Client, filters
from pyrogram.types import Message

from helpers.ai_recommendations import get_ai_recommendations, get_mood_playlist
from helpers.decorators import anti_flood
from helpers.utils import sanitize_html
from strings.buttons import recommendation_keyboard
from strings.messages import MOOD_HEADER, RECOMMEND_HEADER, RECOMMEND_LOADING


@Client.on_message(filters.command("recommend") & (filters.group | filters.private))
@anti_flood
async def recommend_command(client: Client, message: Message):
    from bot import cache, db

    msg = await message.reply(RECOMMEND_LOADING)

    user_id = message.from_user.id if message.from_user else 0
    history = await db.get_history(user_id, limit=20)

    recs = await get_ai_recommendations(history)
    if not recs:
        await msg.edit("<b>Could not generate recommendations.</b> Play more songs first!")
        return

    chat_id = message.chat.id
    kb = recommendation_keyboard(recs, chat_id)
    lines = [RECOMMEND_HEADER]
    for i, r in enumerate(recs[:5], 1):
        reason = sanitize_html(r.get("reason", ""))[:80]
        lines.append(
            f"{i}. <b>{sanitize_html(r.get('title', 'Unknown'))}</b> — "
            f"<i>{sanitize_html(r.get('artist', ''))}</i>\n"
            f"   <i>{reason}</i>"
        )
    await msg.edit("\n".join(lines), reply_markup=kb)


@Client.on_message(filters.command("mood") & (filters.group | filters.private))
@anti_flood
async def mood_command(client: Client, message: Message):
    from bot import cache

    args = message.command[1:]
    mood = " ".join(args) if args else "chill"

    msg = await message.reply(f"<b>Generating {sanitize_html(mood)} playlist...</b>")

    songs = await get_mood_playlist(mood)
    if not songs:
        await msg.edit("<b>Could not generate playlist for that mood.</b>")
        return

    chat_id = message.chat.id
    queued = 0
    for song in songs:
        from helpers.downloader import resolve_to_youtube
        query = f"{song.get('title', '')} {song.get('artist', '')}"
        track = await resolve_to_youtube(query)
        if track:
            await cache.add_to_queue(chat_id, track)
            queued += 1

    if not await cache.is_stream_active(chat_id) and queued > 0:
        first = await cache.pop_queue(chat_id)
        if first:
            from plugins.play import _start_stream_from_track
            await _start_stream_from_track(client, chat_id, first)

    await msg.edit(
        MOOD_HEADER.format(mood=sanitize_html(mood)) +
        f"\n\n{queued} songs added to queue."
    )
