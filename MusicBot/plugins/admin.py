from pyrogram import Client, filters
from pyrogram.types import Message

from helpers.decorators import is_admin, is_owner
from helpers.utils import format_duration, sanitize_html
from strings.messages import (
    ERROR_NOT_IN_VC,
    LOOP_SET,
    NO_ACTIVE_STREAM,
    PAUSED,
    REPLAYED,
    RESUMED,
    SKIPPED,
    STOPPED,
    VOLUME_SET,
)


@Client.on_message(filters.command("pause") & (filters.group | filters.channel))
@is_admin
async def pause_command(client: Client, message: Message):
    from bot import assistant_manager, cache
    if not await cache.is_stream_active(message.chat.id):
        await message.reply(NO_ACTIVE_STREAM)
        return
    await assistant_manager.pause(message.chat.id)
    await message.reply(PAUSED)


@Client.on_message(filters.command("resume") & (filters.group | filters.channel))
@is_admin
async def resume_command(client: Client, message: Message):
    from bot import assistant_manager, cache
    if not await cache.is_stream_active(message.chat.id):
        await message.reply(NO_ACTIVE_STREAM)
        return
    await assistant_manager.resume(message.chat.id)
    await message.reply(RESUMED)


@Client.on_message(filters.command("skip") & (filters.group | filters.channel))
@is_admin
async def skip_command(client: Client, message: Message):
    from bot import cache
    if not await cache.is_stream_active(message.chat.id):
        await message.reply(NO_ACTIVE_STREAM)
        return
    from plugins.play import _play_next
    await message.reply(SKIPPED)
    await _play_next(client, message.chat.id)


@Client.on_message(filters.command("stop") & (filters.group | filters.channel))
@is_admin
async def stop_command(client: Client, message: Message):
    from bot import assistant_manager, cache
    chat_id = message.chat.id
    await cache.clear_queue(chat_id)
    await cache.clear_now_playing(chat_id)
    await cache.set_stream_active(chat_id, False)
    await assistant_manager.leave_vc(chat_id)
    await message.reply(STOPPED)


@Client.on_message(filters.command("replay") & (filters.group | filters.channel))
@is_admin
async def replay_command(client: Client, message: Message):
    from bot import assistant_manager, cache
    from helpers.downloader import get_audio_stream_url
    from helpers.effects import get_filter

    track = await cache.get_now_playing(message.chat.id)
    if not track:
        await message.reply(NO_ACTIVE_STREAM)
        return
    effect = await cache.get_effect(message.chat.id)
    ffmpeg_filter = get_filter(effect)
    stream_url = await get_audio_stream_url(track.get("url", ""))
    if not stream_url:
        await message.reply("<b>Could not replay. Stream URL expired.</b>")
        return
    ffmpeg_args = ["-af", ffmpeg_filter] if ffmpeg_filter else []
    await assistant_manager.change_stream(message.chat.id, stream_url, ffmpeg_args)
    await message.reply(REPLAYED)


@Client.on_message(filters.command("volume") & (filters.group | filters.channel))
@is_admin
async def volume_command(client: Client, message: Message):
    from bot import assistant_manager, cache
    args = message.command
    if len(args) < 2 or not args[1].isdigit():
        vol = await cache.get_volume(message.chat.id)
        await message.reply(f"<b>Current volume:</b> {vol}%\nUsage: <code>/volume [0-200]</code>")
        return
    volume = max(0, min(200, int(args[1])))
    await cache.set_volume(message.chat.id, volume)
    await assistant_manager.change_volume(message.chat.id, volume)
    await message.reply(VOLUME_SET.format(volume=volume))


@Client.on_message(filters.command("loop") & (filters.group | filters.channel))
@is_admin
async def loop_command(client: Client, message: Message):
    from bot import cache
    args = message.command
    modes = {"off": "off", "one": "one", "all": "all"}
    if len(args) > 1 and args[1].lower() in modes:
        mode = args[1].lower()
    else:
        current = await cache.get_loop(message.chat.id)
        cycle = {"off": "one", "one": "all", "all": "off"}
        mode = cycle.get(current, "off")
    await cache.set_loop(message.chat.id, mode)
    await message.reply(LOOP_SET.format(mode=mode))


@Client.on_message(filters.command("seek") & (filters.group | filters.channel))
@is_admin
async def seek_command(client: Client, message: Message):
    await message.reply("<b>Seek is not supported with stream piping. Use /replay to restart.</b>")


@Client.on_message(filters.command("ping") & (filters.group | filters.private))
async def ping_command(client: Client, message: Message):
    import time
    from bot import cache, db
    start = time.monotonic()
    await message.reply("...")
    latency = (time.monotonic() - start) * 1000

    try:
        redis_ms = await cache.ping()
    except Exception:
        redis_ms = -1

    try:
        import time as t
        s = t.monotonic()
        await db.db.command("ping")
        mongo_ms = (t.monotonic() - s) * 1000
    except Exception:
        mongo_ms = -1

    await message.reply(
        f"<b>Pong!</b>\n\n"
        f"Bot: <code>{latency:.0f}ms</code>\n"
        f"Redis: <code>{redis_ms:.0f}ms</code>\n"
        f"MongoDB: <code>{mongo_ms:.0f}ms</code>"
    )


@Client.on_message(filters.command("uptime") & (filters.group | filters.private))
async def uptime_command(client: Client, message: Message):
    import time
    from helpers.utils import get_readable_time
    # Store start time in bot module
    try:
        import bot as bot_module
        start = getattr(bot_module, "_start_time", time.time())
        uptime = int(time.time() - start)
        await message.reply(f"<b>Uptime:</b> {get_readable_time(uptime)}")
    except Exception:
        await message.reply("<b>Uptime information unavailable.</b>")


@Client.on_message(filters.command("enable247") & (filters.group | filters.channel))
@is_admin
async def enable247_command(client: Client, message: Message):
    from bot import db
    state = await db.toggle_247(message.chat.id)
    status = "enabled" if state else "disabled"
    await message.reply(f"<b>24/7 mode {status}.</b> {'Bot will stay in VC even when queue is empty.' if state else 'Bot will leave VC when queue is empty.'}")
