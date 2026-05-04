from pyrogram import Client
from pyrogram.types import CallbackQuery

from helpers.effects import effects_keyboard
from helpers.utils import format_duration, sanitize_html
from strings.messages import NOW_PLAYING, PAUSED, RESUMED, SKIPPED, STOPPED, VOLUME_SET


def _safe_int(val: str, default: int = 0) -> int:
    try:
        return int(val)
    except (ValueError, TypeError):
        return default


@Client.on_callback_query()
async def handle_callbacks(client: Client, query: CallbackQuery):
    data = query.data
    if not data:
        return

    parts = data.split("|")
    action = parts[0]

    if action == "noop":
        await query.answer()
        return

    if action == "help":
        if len(parts) >= 2:
            await _handle_help(client, query, _safe_int(parts[1], 0))
        return

    if action == "qpage":
        if len(parts) >= 3:
            await _handle_qpage(client, query, _safe_int(parts[1], 0), _safe_int(parts[2], 0))
        return

    if action == "lpage":
        if len(parts) >= 3:
            await _handle_lpage(client, query, _safe_int(parts[1], 0), _safe_int(parts[2], 0))
        return

    if action == "effects_menu":
        if len(parts) >= 2:
            await _handle_effects_menu(client, query, _safe_int(parts[1], 0))
        return

    if action == "effect":
        if len(parts) >= 2:
            await _handle_effect_set(client, query, parts[1])
        return

    if action == "fav_page":
        if len(parts) >= 3:
            await _handle_fav_page(client, query, _safe_int(parts[1], 0), _safe_int(parts[2], 0))
        return

    if action == "fav_play":
        if len(parts) >= 3:
            await _handle_fav_play(client, query, parts[1], parts[2])
        return

    if action == "radio_play":
        if len(parts) >= 3:
            await _handle_radio_play(client, query, _safe_int(parts[1], 0), parts[2])
        return

    if action == "id_play":
        if len(parts) >= 3:
            await _handle_id_play(client, query, _safe_int(parts[1], 0), parts[2])
        return
    if action == "id_lyrics":
        if len(parts) >= 4:
            await _handle_id_lyrics(client, query, parts)
        return
    if action == "id_more":
        if len(parts) >= 3:
            await _handle_id_more(client, query, _safe_int(parts[1], 0), parts[2])
        return

    if action == "rec_play":
        if len(parts) >= 4:
            await _handle_rec_play(client, query, parts)
        return

    if action == "vs_skip":
        if len(parts) >= 2:
            await _handle_voteskip(client, query, _safe_int(parts[1], 0), "skip")
        return
    if action == "vs_keep":
        if len(parts) >= 2:
            await _handle_voteskip(client, query, _safe_int(parts[1], 0), "keep")
        return

    # Now playing controls — require chat_id
    if len(parts) < 2:
        await query.answer()
        return

    chat_id = _safe_int(parts[1])
    if not chat_id:
        await query.answer()
        return

    from bot import assistant_manager, cache

    if action == "pause":
        np = await cache.get_now_playing(chat_id)
        is_paused = np.get("paused", False) if np else False
        if is_paused:
            await assistant_manager.resume(chat_id)
            if np:
                np["paused"] = False
                await cache.set_now_playing(chat_id, np)
            await query.answer("Resumed")
        else:
            await assistant_manager.pause(chat_id)
            if np:
                np["paused"] = True
                await cache.set_now_playing(chat_id, np)
            await query.answer("Paused")
        await _refresh_np(client, query, chat_id)
        return

    if action == "skip":
        from plugins.play import _play_next
        await query.answer("Skipping...")
        await _play_next(client, chat_id)
        return

    if action == "stop":
        await cache.clear_queue(chat_id)
        await cache.clear_now_playing(chat_id)
        await cache.set_stream_active(chat_id, False)
        await assistant_manager.leave_vc(chat_id)
        await query.answer("Stopped")
        try:
            await query.message.edit_caption("<b>Playback stopped.</b>", reply_markup=None)
        except Exception:
            pass
        return

    if action == "prev":
        await query.answer("No previous track available.")
        return

    if action == "shuffle":
        await cache.shuffle_queue(chat_id)
        await query.answer("Queue shuffled!")
        return

    if action == "loop":
        current = await cache.get_loop(chat_id)
        cycle = {"off": "one", "one": "all", "all": "off"}
        new_mode = cycle.get(current, "off")
        await cache.set_loop(chat_id, new_mode)
        await query.answer(f"Loop: {new_mode}")
        await _refresh_np(client, query, chat_id)
        return

    if action == "vol_down":
        vol = await cache.get_volume(chat_id)
        new_vol = max(0, vol - 10)
        await cache.set_volume(chat_id, new_vol)
        try:
            await assistant_manager.change_volume(chat_id, new_vol)
        except Exception:
            pass
        await query.answer(f"Volume: {new_vol}%")
        await _refresh_np(client, query, chat_id)
        return

    if action == "vol_up":
        vol = await cache.get_volume(chat_id)
        new_vol = min(200, vol + 10)
        await cache.set_volume(chat_id, new_vol)
        try:
            await assistant_manager.change_volume(chat_id, new_vol)
        except Exception:
            pass
        await query.answer(f"Volume: {new_vol}%")
        await _refresh_np(client, query, chat_id)
        return

    if action == "queue":
        queue = await cache.get_queue(chat_id)
        if not queue:
            await query.answer("Queue is empty!", show_alert=True)
            return
        from helpers.utils import split_pages
        from strings.buttons import queue_keyboard
        pages = split_pages(queue, 5)
        lines = [f"<b>Queue — {len(queue)} songs</b>\n"]
        for i, t in enumerate(pages[0]):
            lines.append(f"{i+1}. <b>{sanitize_html(t.get('title','Unknown')[:40])}</b>")
        kb = queue_keyboard(chat_id, 0, len(pages))
        try:
            await query.message.reply("\n".join(lines), reply_markup=kb)
        except Exception:
            pass
        await query.answer()
        return

    if action == "lyrics":
        np = await cache.get_now_playing(chat_id)
        if not np:
            await query.answer("No song playing.", show_alert=True)
            return
        from helpers.lyrics import get_lyrics, paginate_lyrics
        result = await get_lyrics(np.get("title", ""), np.get("artist", ""))
        if not result:
            await query.answer("Lyrics not found.", show_alert=True)
            return
        pages = paginate_lyrics(result["lyrics"])
        from strings.buttons import lyrics_keyboard
        from strings.messages import LYRICS_HEADER
        header = LYRICS_HEADER.format(
            title=sanitize_html(result["title"]),
            artist=sanitize_html(result["artist"]),
            source=result.get("source", ""),
        )
        kb = lyrics_keyboard(0, len(pages), chat_id)
        try:
            await query.message.reply(header + pages[0], reply_markup=kb)
        except Exception:
            pass
        await query.answer()
        return

    if action == "fav":
        from bot import db
        np = await cache.get_now_playing(chat_id)
        if not np:
            await query.answer("No song playing.", show_alert=True)
            return
        user_id = query.from_user.id
        if await db.is_favourite(user_id, np.get("video_id", "")):
            await db.remove_favourite(user_id, np.get("video_id", ""))
            await query.answer("Removed from favourites.")
        else:
            await db.add_favourite(user_id, dict(np))
            await query.answer("Added to favourites!")
        return

    if action == "download":
        await query.answer("Use /download command to get the current song.", show_alert=True)
        return

    if action == "source":
        np = await cache.get_now_playing(chat_id)
        if np:
            url = np.get("url", "No URL available")
            await query.answer(f"Source: {url[:100]}", show_alert=True)
        else:
            await query.answer("No song playing.", show_alert=True)
        return

    if action == "rate":
        from bot import db
        np = await cache.get_now_playing(chat_id)
        if not np:
            await query.answer("No song playing.", show_alert=True)
            return
        vote = _safe_int(parts[2], 1) if len(parts) > 2 else 1
        await db.rate_song(chat_id, np.get("video_id", ""), query.from_user.id, vote)
        label = "Liked!" if vote == 1 else "Disliked!"
        await query.answer(label)
        return

    if action == "voteskip":
        from plugins.voting import _start_voteskip
        await _start_voteskip(client, query, chat_id)
        return

    if action == "np_back":
        await query.answer()
        return

    await query.answer()


async def _refresh_np(client, query, chat_id: int):
    from bot import cache
    from helpers.utils import progress_bar
    from strings.buttons import now_playing_keyboard

    np = await cache.get_now_playing(chat_id)
    if not np:
        return
    loop = await cache.get_loop(chat_id)
    effect = await cache.get_effect(chat_id)
    volume = await cache.get_volume(chat_id)
    queue = await cache.get_queue(chat_id)
    is_paused = np.get("paused", False)

    caption = NOW_PLAYING.format(
        title=sanitize_html(np.get("title", "Unknown")),
        artist=sanitize_html(np.get("artist", "Unknown")),
        platform=np.get("platform", "YouTube"),
        duration=format_duration(np.get("duration") or 0),
        requester=sanitize_html(np.get("requester_name", "User")),
        queue_pos=f"1/{len(queue) + 1}",
        effect=effect,
        loop=loop,
        volume=volume,
        progress_bar=progress_bar(0, 1),
    )
    keyboard = now_playing_keyboard(chat_id, is_paused=is_paused, loop=loop, effect=effect)
    try:
        await query.message.edit_caption(caption=caption, reply_markup=keyboard)
    except Exception:
        try:
            await query.message.edit_text(caption, reply_markup=keyboard)
        except Exception:
            pass


async def _handle_help(client, query, page: int):
    from strings.buttons import help_keyboard
    from strings.messages import HELP_ADMIN, HELP_GAMES, HELP_INFO, HELP_MUSIC
    pages = [HELP_MUSIC, HELP_ADMIN, HELP_GAMES, HELP_INFO]
    page = max(0, min(page, len(pages) - 1))
    text = pages[page]
    kb = help_keyboard(page)
    try:
        await query.message.edit_text(text, reply_markup=kb)
    except Exception:
        pass
    await query.answer()


async def _handle_qpage(client, query, chat_id: int, page: int):
    from bot import cache
    from helpers.utils import split_pages
    from strings.buttons import queue_keyboard
    queue = await cache.get_queue(chat_id)
    if not queue:
        await query.answer("Queue is empty!", show_alert=True)
        return
    pages = split_pages(queue, 5)
    page = max(0, min(page, len(pages) - 1))
    offset = page * 5
    lines = [f"<b>Queue — {len(queue)} songs</b>\n"]
    for i, t in enumerate(pages[page]):
        lines.append(f"{offset+i+1}. <b>{sanitize_html(t.get('title','Unknown')[:40])}</b>")
    kb = queue_keyboard(chat_id, page, len(pages))
    try:
        await query.message.edit_text("\n".join(lines), reply_markup=kb)
    except Exception:
        pass
    await query.answer()


async def _handle_lpage(client, query, chat_id: int, page: int):
    await query.answer("Navigate lyrics with the buttons.")


async def _handle_effects_menu(client, query, chat_id: int):
    from bot import cache
    from pyrogram.types import InlineKeyboardMarkup
    current = await cache.get_effect(chat_id)
    kb = effects_keyboard(current)
    try:
        await query.message.edit_text(
            "<b>Select audio effect:</b>",
            reply_markup=InlineKeyboardMarkup(kb),
        )
    except Exception:
        pass
    await query.answer()


async def _handle_effect_set(client, query, effect_name: str):
    from bot import assistant_manager, cache
    from helpers.downloader import get_audio_stream_url
    from helpers.effects import EFFECT_NAMES, get_filter

    if effect_name not in EFFECT_NAMES:
        await query.answer("Unknown effect.", show_alert=True)
        return

    chat_id = query.message.chat.id
    await cache.set_effect(chat_id, effect_name)

    np = await cache.get_now_playing(chat_id)
    if np:
        try:
            ffmpeg_filter = get_filter(effect_name)
            stream_url = await get_audio_stream_url(np.get("url", ""))
            if stream_url:
                ffmpeg_args = ["-af", ffmpeg_filter] if ffmpeg_filter else []
                await assistant_manager.change_stream(chat_id, stream_url, ffmpeg_args)
        except Exception as e:
            from loguru import logger
            logger.error(f"Effect change stream error: {e}")

    await query.answer(f"Effect: {effect_name}")
    try:
        from strings.buttons import now_playing_keyboard
        loop = await cache.get_loop(chat_id)
        kb = now_playing_keyboard(chat_id, loop=loop, effect=effect_name)
        await query.message.edit_text(
            f"<b>Effect set to: {effect_name}</b>",
            reply_markup=kb,
        )
    except Exception:
        pass


async def _handle_fav_page(client, query, user_id: int, page: int):
    from bot import db
    from helpers.utils import split_pages
    from strings.buttons import favlist_keyboard
    favs = await db.get_favourites(user_id)
    if not favs:
        await query.answer("No favourites.", show_alert=True)
        return
    pages = split_pages(favs, 8)
    page = max(0, min(page, len(pages) - 1))
    text = f"<b>Your Favourites — {len(favs)} songs</b>\n\nPage {page+1}/{len(pages)}"
    kb = favlist_keyboard(pages[page], page, len(pages), user_id)
    try:
        await query.message.edit_text(text, reply_markup=kb)
    except Exception:
        pass
    await query.answer()


async def _handle_fav_play(client, query, user_id: str, video_id: str):
    from bot import db, cache
    favs = await db.get_favourites(int(user_id))
    track = next((f for f in favs if f.get("video_id") == video_id), None)
    if not track:
        await query.answer("Track not found.", show_alert=True)
        return
    chat_id = query.message.chat.id
    if await cache.is_stream_active(chat_id):
        await cache.add_to_queue(chat_id, track)
        await query.answer("Added to queue!")
    else:
        from plugins.play import _start_stream_from_track
        await _start_stream_from_track(client, chat_id, track)
        await query.answer("Playing!")


async def _handle_radio_play(client, query, chat_id: int, station_name: str):
    from bot import assistant_manager, cache, db
    stations = await db.get_radio_stations()
    station = next((s for s in stations if s.get("name", "").lower() == station_name.lower()), None)
    if not station:
        await query.answer("Station not found.", show_alert=True)
        return

    stream_url = station.get("url", "")
    track = {
        "title": station.get("name", "Radio"),
        "artist": station.get("genre", "Radio"),
        "url": stream_url,
        "video_id": stream_url,
        "platform": "radio",
        "duration": 0,
    }

    if await cache.is_stream_active(chat_id):
        await cache.clear_queue(chat_id)
    ok = await assistant_manager.play_audio(chat_id, stream_url)
    if ok:
        await cache.set_now_playing(chat_id, track)
        await cache.set_stream_active(chat_id, True)
        await query.answer(f"Streaming: {station.get('name')}")
        try:
            await query.message.edit_text(f"📻 <b>Streaming: {sanitize_html(station.get('name', 'Radio'))}</b>")
        except Exception:
            pass
    else:
        await query.answer("Failed to start stream.", show_alert=True)


async def _handle_id_play(client, query, chat_id: int, title_query: str):
    from bot import cache
    from plugins.play import _resolve_track

    class FakeMsg:
        chat = type("C", (), {"id": chat_id})()
        from_user = query.from_user
        async def reply(self, text): pass

    track = await _resolve_track(title_query, FakeMsg())
    if not track:
        await query.answer("Track not found.", show_alert=True)
        return
    if await cache.is_stream_active(chat_id):
        await cache.add_to_queue(chat_id, track)
        await query.answer("Added to queue!")
    else:
        from plugins.play import _start_stream_from_track
        await _start_stream_from_track(client, chat_id, track)
        await query.answer("Playing!")


async def _handle_id_lyrics(client, query, parts: list):
    if len(parts) < 4:
        await query.answer()
        return
    title = parts[2]
    artist = parts[3]
    from helpers.lyrics import get_lyrics, paginate_lyrics
    result = await get_lyrics(title, artist)
    if not result:
        await query.answer("Lyrics not found.", show_alert=True)
        return
    pages = paginate_lyrics(result["lyrics"])
    from strings.messages import LYRICS_HEADER
    header = LYRICS_HEADER.format(
        title=sanitize_html(result["title"]),
        artist=sanitize_html(result["artist"]),
        source=result.get("source", ""),
    )
    try:
        await query.message.reply(header + pages[0])
    except Exception:
        pass
    await query.answer()


async def _handle_id_more(client, query, chat_id: int, artist: str):
    from helpers.downloader import search_youtube
    results = await search_youtube(f"{artist} songs", limit=5)
    if not results:
        await query.answer("No results found.", show_alert=True)
        return
    lines = [f"<b>Songs by {sanitize_html(artist)}:</b>\n"]
    for r in results:
        lines.append(f"• <b>{sanitize_html(r.get('title', 'Unknown')[:50])}</b>")
    try:
        await query.message.reply("\n".join(lines))
    except Exception:
        pass
    await query.answer()


async def _handle_rec_play(client, query, parts: list):
    if len(parts) < 4:
        await query.answer()
        return
    chat_id = _safe_int(parts[1])
    title = parts[2]
    artist = parts[3]
    from bot import cache
    from plugins.play import _resolve_track

    class FakeMsg:
        chat = type("C", (), {"id": chat_id})()
        from_user = query.from_user
        async def reply(self, text): pass

    track = await _resolve_track(f"{title} {artist}", FakeMsg())
    if not track:
        await query.answer("Track not found.", show_alert=True)
        return
    if await cache.is_stream_active(chat_id):
        await cache.add_to_queue(chat_id, track)
        await query.answer("Added to queue!")
    else:
        from plugins.play import _start_stream_from_track
        await _start_stream_from_track(client, chat_id, track)
        await query.answer("Playing!")


async def _handle_voteskip(client, query, chat_id: int, action: str):
    from bot import cache, db
    if action == "keep":
        await query.answer("You voted to keep the song!")
        return

    count = await cache.add_vote_skip(chat_id, query.from_user.id)
    threshold = await db.get_vote_skip_threshold(chat_id)

    if count >= threshold:
        await cache.clear_vote_skip(chat_id)
        from plugins.play import _play_next
        await query.answer("Vote skip passed!", show_alert=True)
        await _play_next(client, chat_id)
        try:
            from strings.messages import VOTE_SKIP_DONE
            await query.message.edit_text(VOTE_SKIP_DONE)
        except Exception:
            pass
    else:
        needed = threshold - count
        await query.answer(f"Vote recorded! Need {needed} more votes.")
        from strings.buttons import vote_skip_keyboard
        try:
            await query.message.edit_reply_markup(vote_skip_keyboard(chat_id, count, 0))
        except Exception:
            pass
