import asyncio
import os
from typing import Optional

from loguru import logger
from pyrogram import Client, filters
from pyrogram.types import Message

from helpers.decorators import anti_flood, maintenance_check, private_bot_check
from helpers.downloader import (
    detect_platform,
    get_audio_stream_url,
    get_info,
    is_valid_url,
    resolve_to_youtube,
    search_youtube,
)
from helpers.effects import get_filter
from helpers.thumbnail import generate_np_thumbnail
from helpers.utils import format_duration, progress_bar, sanitize_html, truncate
from strings.buttons import now_playing_keyboard
from strings.messages import (
    ADDED_TO_QUEUE,
    DOWNLOADING,
    ERROR_DOWNLOAD,
    ERROR_NO_RESULTS,
    NOW_PLAYING,
    QUEUE_EMPTY,
    SEARCHING,
)


async def _resolve_track(url_or_query: str, message: Message) -> Optional[dict]:
    """Resolve any input to a streamable track dict."""
    if is_valid_url(url_or_query):
        platform = detect_platform(url_or_query)

        if platform == "spotify":
            from helpers.spotify import resolve_spotify_url
            tracks = await resolve_spotify_url(url_or_query)
            if not tracks:
                return None
            if len(tracks) == 1:
                t = tracks[0]
                query = t.get("search_query") or f"{t['title']} {t.get('artist', '')}"
                return await resolve_to_youtube(query) or None
            # Playlist — queue all but return first
            first = None
            for t in tracks:
                query = t.get("search_query") or f"{t['title']} {t.get('artist', '')}"
                resolved = await resolve_to_youtube(query)
                if resolved and not first:
                    first = resolved
                elif resolved:
                    await _add_to_queue(message.chat.id, resolved, message)
            return first

        if platform == "apple":
            from helpers.apple_music import resolve_apple_music
            meta = await resolve_apple_music(url_or_query)
            if meta:
                return await resolve_to_youtube(meta["search_query"])
            return None

        if platform == "resso":
            from helpers.resso import resolve_resso
            meta = await resolve_resso(url_or_query)
            if meta:
                return await resolve_to_youtube(meta["search_query"])
            return None

        if platform == "tidal":
            from helpers.tidal import resolve_tidal
            meta = await resolve_tidal(url_or_query)
            if meta:
                return await resolve_to_youtube(meta["search_query"])
            return None

        if platform == "deezer":
            from helpers.deezer import resolve_deezer_url
            tracks = await resolve_deezer_url(url_or_query)
            if tracks:
                first = None
                for t in tracks:
                    query = t.get("search_query") or f"{t['title']} {t.get('artist', '')}"
                    resolved = await resolve_to_youtube(query)
                    if resolved and not first:
                        first = resolved
                    elif resolved:
                        await _add_to_queue(message.chat.id, resolved, message)
                return first
            return None

        if platform == "jiosaavn":
            from helpers.jiosaavn import resolve_jiosaavn_url
            meta = await resolve_jiosaavn_url(url_or_query)
            if meta and meta.get("stream_url"):
                return {
                    "title": meta["title"],
                    "artist": meta.get("artist", ""),
                    "thumbnail": meta.get("thumbnail", ""),
                    "duration": meta.get("duration", 0),
                    "url": meta["stream_url"],
                    "video_id": url_or_query,
                    "platform": "jiosaavn",
                }
            return None

        if platform == "soundcloud":
            from helpers.soundcloud import resolve_soundcloud
            return await resolve_soundcloud(url_or_query)

        # YouTube or unknown URL — get info directly
        info = await get_info(url_or_query)
        if info:
            return {
                "title": info.get("title", "Unknown"),
                "artist": info.get("uploader", ""),
                "thumbnail": info.get("thumbnail"),
                "duration": info.get("duration", 0),
                "url": url_or_query,
                "video_id": info.get("id", url_or_query),
                "platform": platform if platform != "unknown" else "youtube",
            }
        return None

    # Plain text search
    results = await search_youtube(url_or_query, limit=1)
    if not results:
        return None
    r = results[0]
    return {
        "title": r.get("title", "Unknown"),
        "artist": r.get("uploader", ""),
        "thumbnail": r.get("thumbnail"),
        "duration": r.get("duration", 0),
        "url": f"https://www.youtube.com/watch?v={r.get('id', '')}",
        "video_id": r.get("id", ""),
        "platform": "youtube",
    }


async def _add_to_queue(chat_id: int, track: dict, message: Message):
    from bot import cache, db
    pos = await cache.add_to_queue(chat_id, track)
    await message.reply(
        ADDED_TO_QUEUE.format(title=sanitize_html(track["title"]), pos=pos)
    )


async def _start_stream(client: Client, message: Message, track: dict):
    from bot import assistant_manager, cache, db
    chat_id = message.chat.id

    effect = await cache.get_effect(chat_id)
    ffmpeg_filter = get_filter(effect)
    stream_url = await get_audio_stream_url(track.get("url", ""))

    if not stream_url:
        await message.reply(ERROR_DOWNLOAD)
        return

    ffmpeg_args = ["-af", ffmpeg_filter] if ffmpeg_filter else []
    ok = await assistant_manager.play_audio(chat_id, stream_url, ffmpeg_args)
    if not ok:
        await message.reply("<b>Could not start stream. Check bot permissions in voice chat.</b>")
        return

    await cache.set_now_playing(chat_id, track)
    await cache.set_stream_active(chat_id, True)

    # Track listening history
    requester = message.from_user
    if requester:
        track_copy = dict(track)
        track_copy["chat_id"] = chat_id
        track_copy["requester_id"] = requester.id
        track_copy["requester_name"] = requester.first_name or "User"
        await db.add_to_history(requester.id, track_copy)

    # Send Now Playing message
    volume = await cache.get_volume(chat_id)
    loop_mode = await cache.get_loop(chat_id)
    queue = await cache.get_queue(chat_id)
    duration_str = format_duration(track.get("duration") or 0)
    requester_name = (message.from_user.first_name or "User") if message.from_user else "Unknown"

    caption = NOW_PLAYING.format(
        title=sanitize_html(track.get("title", "Unknown")),
        artist=sanitize_html(track.get("artist", "Unknown")),
        platform=track.get("platform", "YouTube"),
        duration=duration_str,
        requester=sanitize_html(requester_name),
        queue_pos=f"1/{len(queue) + 1}",
        effect=effect,
        loop=loop_mode,
        volume=volume,
        progress_bar=progress_bar(0, 1),
    )

    keyboard = now_playing_keyboard(chat_id, loop=loop_mode, effect=effect)
    thumb = await generate_np_thumbnail(
        title=track.get("title", "Unknown"),
        artist=track.get("artist", "Unknown"),
        duration=duration_str,
        platform=track.get("platform", "YouTube"),
        requester=requester_name,
        thumb_url=track.get("thumbnail"),
    )

    try:
        if thumb:
            import io
            nm = await client.send_photo(
                chat_id,
                photo=io.BytesIO(thumb),
                caption=caption,
                reply_markup=keyboard,
            )
        else:
            nm = await client.send_message(chat_id, caption, reply_markup=keyboard)
        await cache.set_np_message(chat_id, nm.id)
    except Exception as e:
        logger.error(f"NP message error: {e}")

    # Stream end is handled centrally by bot.py's _register_stream_end_handlers()


async def _play_next(client: Client, chat_id: int):
    from bot import assistant_manager, cache, db
    loop = await cache.get_loop(chat_id)
    current = await cache.get_now_playing(chat_id)

    if loop == "one" and current:
        await _start_stream_from_track(client, chat_id, current)
        return

    next_track = await cache.pop_queue(chat_id)
    if not next_track:
        if loop == "all" and current:
            await cache.add_to_queue(chat_id, current)
            next_track = await cache.pop_queue(chat_id)
        else:
            await cache.clear_now_playing(chat_id)
            await cache.set_stream_active(chat_id, False)
            try:
                from config import AUTO_LEAVING_ASSISTANT, ASSISTANT_LEAVE_TIME
                if AUTO_LEAVING_ASSISTANT:
                    await asyncio.sleep(ASSISTANT_LEAVE_TIME)
                    if not await cache.is_stream_active(chat_id):
                        mode_247 = await db.is_247_mode(chat_id)
                        if not mode_247:
                            await assistant_manager.leave_vc(chat_id)
            except Exception as e:
                logger.error(f"Auto-leave error: {e}")
            return

    effect = await cache.get_effect(chat_id)
    ffmpeg_filter = get_filter(effect)
    stream_url = await get_audio_stream_url(next_track.get("url", ""))
    if not stream_url:
        await _play_next(client, chat_id)
        return

    ffmpeg_args = ["-af", ffmpeg_filter] if ffmpeg_filter else []
    await assistant_manager.change_stream(chat_id, stream_url, ffmpeg_args)
    await cache.set_now_playing(chat_id, next_track)

    volume = await cache.get_volume(chat_id)
    loop_mode = await cache.get_loop(chat_id)
    queue = await cache.get_queue(chat_id)
    duration_str = format_duration(next_track.get("duration") or 0)

    caption = NOW_PLAYING.format(
        title=sanitize_html(next_track.get("title", "Unknown")),
        artist=sanitize_html(next_track.get("artist", "Unknown")),
        platform=next_track.get("platform", "YouTube"),
        duration=duration_str,
        requester=sanitize_html(next_track.get("requester_name", "Queue")),
        queue_pos=f"1/{len(queue) + 1}",
        effect=effect,
        loop=loop_mode,
        volume=volume,
        progress_bar=progress_bar(0, 1),
    )
    keyboard = now_playing_keyboard(chat_id, loop=loop_mode, effect=effect)

    try:
        nm_id = await cache.get_np_message(chat_id)
        if nm_id:
            await client.edit_message_caption(chat_id, nm_id, caption=caption, reply_markup=keyboard)
    except Exception:
        try:
            nm = await client.send_message(chat_id, caption, reply_markup=keyboard)
            await cache.set_np_message(chat_id, nm.id)
        except Exception as e:
            logger.error(f"NP update error: {e}")


async def _start_stream_from_track(client: Client, chat_id: int, track: dict):
    from bot import assistant_manager, cache
    effect = await cache.get_effect(chat_id)
    ffmpeg_filter = get_filter(effect)
    stream_url = await get_audio_stream_url(track.get("url", ""))
    if not stream_url:
        return
    ffmpeg_args = ["-af", ffmpeg_filter] if ffmpeg_filter else []
    await assistant_manager.change_stream(chat_id, stream_url, ffmpeg_args)


@Client.on_message(filters.command(["play", "p"]) & (filters.group | filters.channel))
@anti_flood
@maintenance_check
@private_bot_check
async def play_command(client: Client, message: Message):
    from bot import cache, db

    # Check if user is gbanned
    if message.from_user and await db.is_gbanned(message.from_user.id):
        await message.reply("<b>You are globally banned from using this bot.</b>")
        return

    query = ""
    if message.reply_to_message:
        if message.reply_to_message.audio or message.reply_to_message.voice or message.reply_to_message.document:
            await _handle_tg_audio(client, message)
            return

    if message.command and len(message.command) > 1:
        query = " ".join(message.command[1:])
    elif message.reply_to_message and message.reply_to_message.text:
        query = message.reply_to_message.text

    if not query:
        await message.reply("<b>Usage:</b> <code>/play [song name or URL]</code>")
        return

    msg = await message.reply(SEARCHING.format(query=sanitize_html(query[:60])))

    track = await _resolve_track(query, message)
    if not track:
        await msg.edit(ERROR_NO_RESULTS.format(query=sanitize_html(query[:60])))
        return

    await msg.edit(DOWNLOADING.format(title=sanitize_html(track.get("title", "Unknown")[:50])))

    chat_id = message.chat.id
    if await cache.is_stream_active(chat_id):
        track["requester_name"] = message.from_user.first_name if message.from_user else "User"
        await cache.add_to_queue(chat_id, track)
        queue = await cache.get_queue(chat_id)
        await msg.edit(ADDED_TO_QUEUE.format(title=sanitize_html(track["title"]), pos=len(queue)))
        return

    await msg.delete()
    await _start_stream(client, message, track)


async def _handle_tg_audio(client: Client, message: Message):
    from bot import cache
    reply = message.reply_to_message
    audio = reply.audio or reply.voice or reply.document
    if not audio:
        return

    msg = await message.reply("<b>Downloading Telegram audio...</b>")
    try:
        path = await client.download_media(reply, file_name=f"downloads/tg_{audio.file_unique_id}.ogg")
        track = {
            "title": getattr(audio, "title", None) or getattr(audio, "file_name", "Telegram Audio") or "Telegram Audio",
            "artist": getattr(audio, "performer", "") or "",
            "duration": getattr(audio, "duration", 0) or 0,
            "url": path,
            "video_id": f"tg_{audio.file_unique_id}",
            "platform": "telegram",
        }
        chat_id = message.chat.id
        if await cache.is_stream_active(chat_id):
            track["requester_name"] = message.from_user.first_name if message.from_user else "User"
            await cache.add_to_queue(chat_id, track)
            queue = await cache.get_queue(chat_id)
            await msg.edit(ADDED_TO_QUEUE.format(title=sanitize_html(track["title"]), pos=len(queue)))
        else:
            await msg.delete()
            await _start_stream(client, message, track)
    except Exception as e:
        await msg.edit(f"<b>Error downloading Telegram audio:</b> <code>{e}</code>")
