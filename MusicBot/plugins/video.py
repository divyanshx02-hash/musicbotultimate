from pyrogram import Client, filters
from pyrogram.types import Message

from helpers.decorators import anti_flood, private_bot_check
from helpers.downloader import get_info, get_video_stream_url, is_valid_url, search_youtube
from helpers.utils import format_duration, sanitize_html
from strings.messages import ADDED_TO_QUEUE, DOWNLOADING, ERROR_DOWNLOAD, ERROR_NO_RESULTS, SEARCHING


@Client.on_message(filters.command(["vplay", "video", "v"]) & (filters.group | filters.channel))
@anti_flood
@private_bot_check
async def vplay_command(client: Client, message: Message):
    from bot import assistant_manager, cache

    query = " ".join(message.command[1:]) if len(message.command) > 1 else ""

    if message.reply_to_message:
        reply = message.reply_to_message
        if reply.video or reply.document:
            await _handle_tg_video(client, message)
            return

    if not query:
        await message.reply("<b>Usage:</b> <code>/vplay [YouTube URL or search query]</code>")
        return

    msg = await message.reply(SEARCHING.format(query=sanitize_html(query[:60])))

    # Resolve to YouTube
    if is_valid_url(query):
        info = await get_info(query)
        if not info:
            await msg.edit(ERROR_NO_RESULTS.format(query=sanitize_html(query)))
            return
        track = {
            "title": info.get("title", "Unknown"),
            "artist": info.get("uploader", ""),
            "thumbnail": info.get("thumbnail"),
            "duration": info.get("duration", 0),
            "url": query,
            "video_id": info.get("id", query),
            "platform": "youtube",
            "is_video": True,
        }
    else:
        results = await search_youtube(query, limit=1)
        if not results:
            await msg.edit(ERROR_NO_RESULTS.format(query=sanitize_html(query)))
            return
        r = results[0]
        track = {
            "title": r.get("title", "Unknown"),
            "artist": r.get("uploader", ""),
            "thumbnail": r.get("thumbnail"),
            "duration": r.get("duration", 0),
            "url": f"https://www.youtube.com/watch?v={r.get('id', '')}",
            "video_id": r.get("id", ""),
            "platform": "youtube",
            "is_video": True,
        }

    await msg.edit(DOWNLOADING.format(title=sanitize_html(track.get("title", "Unknown")[:50])))

    chat_id = message.chat.id
    if await cache.is_stream_active(chat_id):
        track["requester_name"] = message.from_user.first_name if message.from_user else "User"
        await cache.add_to_queue(chat_id, track)
        queue = await cache.get_queue(chat_id)
        await msg.edit(ADDED_TO_QUEUE.format(title=sanitize_html(track["title"]), pos=len(queue)))
        return

    stream_url = await get_video_stream_url(track["url"])
    if not stream_url:
        await msg.edit(ERROR_DOWNLOAD)
        return

    ok = await assistant_manager.play_video(chat_id, stream_url)
    if not ok:
        await msg.edit("<b>Could not start video stream. Make sure voice chat supports video.</b>")
        return

    await cache.set_now_playing(chat_id, track)
    await cache.set_stream_active(chat_id, True)

    from strings.buttons import now_playing_keyboard
    loop = await cache.get_loop(chat_id)
    effect = await cache.get_effect(chat_id)
    volume = await cache.get_volume(chat_id)
    queue = await cache.get_queue(chat_id)

    caption = (
        f"🎬 <b>Now Playing (Video)</b>\n\n"
        f"<b>{sanitize_html(track['title'])}</b>\n"
        f"<i>{sanitize_html(track.get('artist', ''))}</i>\n\n"
        f"Duration: {format_duration(track.get('duration', 0))}\n"
        f"Requested by: {sanitize_html(message.from_user.first_name if message.from_user else 'User')}"
    )
    keyboard = now_playing_keyboard(chat_id, loop=loop, effect=effect)
    nm = await client.send_message(chat_id, caption, reply_markup=keyboard)
    await cache.set_np_message(chat_id, nm.id)
    await msg.delete()


async def _handle_tg_video(client: Client, message: Message):
    from bot import assistant_manager, cache
    reply = message.reply_to_message
    media = reply.video or reply.document
    if not media:
        return

    msg = await message.reply("<b>Processing Telegram video...</b>")
    try:
        path = await client.download_media(reply, file_name=f"downloads/tg_vid_{media.file_unique_id}.mp4")
        track = {
            "title": getattr(media, "file_name", "Telegram Video") or "Telegram Video",
            "artist": "",
            "duration": getattr(media, "duration", 0) or 0,
            "url": path,
            "video_id": f"tg_{media.file_unique_id}",
            "platform": "telegram",
            "is_video": True,
        }
        chat_id = message.chat.id
        if await cache.is_stream_active(chat_id):
            await cache.add_to_queue(chat_id, track)
            queue = await cache.get_queue(chat_id)
            await msg.edit(ADDED_TO_QUEUE.format(title=sanitize_html(track["title"]), pos=len(queue)))
        else:
            ok = await assistant_manager.play_video(chat_id, path)
            if not ok:
                await msg.edit("<b>Could not start video stream.</b>")
                return
            await cache.set_now_playing(chat_id, track)
            await cache.set_stream_active(chat_id, True)
            await msg.edit(f"🎬 <b>Now Playing:</b> {sanitize_html(track['title'])}")
    except Exception as e:
        await msg.edit(f"<b>Error:</b> <code>{e}</code>")
