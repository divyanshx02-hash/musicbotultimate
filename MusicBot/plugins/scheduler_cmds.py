import asyncio
from datetime import datetime, timedelta, timezone

from pyrogram import Client, filters
from pyrogram.types import Message

from helpers.decorators import anti_flood, is_admin
from helpers.utils import parse_time_arg, sanitize_html
from strings.messages import ALARM_SET, SCHEDULE_SET, SLEEP_SET


@Client.on_message(filters.command("sleep") & (filters.group | filters.channel))
@is_admin
async def sleep_command(client: Client, message: Message):
    args = message.command[1:]
    if not args:
        await message.reply("<b>Usage:</b> <code>/sleep [minutes]</code>")
        return

    seconds = parse_time_arg(args[0])
    if not seconds:
        await message.reply("<b>Invalid time format.</b> Example: <code>/sleep 30</code>")
        return

    minutes = seconds // 60 if seconds >= 60 else seconds
    chat_id = message.chat.id
    await message.reply(SLEEP_SET.format(minutes=minutes))

    async def stop_after():
        await asyncio.sleep(seconds)
        from bot import assistant_manager, cache
        if await cache.is_stream_active(chat_id):
            await cache.clear_queue(chat_id)
            await cache.set_stream_active(chat_id, False)
            await assistant_manager.leave_vc(chat_id)
            try:
                await client.send_message(chat_id, "<b>Sleep timer reached. Music stopped.</b>")
            except Exception:
                pass

    asyncio.create_task(stop_after())


@Client.on_message(filters.command("schedule") & (filters.group | filters.channel))
@is_admin
async def schedule_command(client: Client, message: Message):
    args = message.command[1:]
    if len(args) < 2:
        await message.reply("<b>Usage:</b> <code>/schedule HH:MM [song]</code>\nExample: <code>/schedule 20:30 lofi music</code>")
        return

    time_str = args[0]
    query = " ".join(args[1:])

    try:
        hour, minute = map(int, time_str.split(":"))
    except ValueError:
        await message.reply("<b>Invalid time format. Use HH:MM</b>")
        return

    from bot import db
    tz_name = await db.get_chat_timezone(message.chat.id)
    try:
        import pytz
        tz = pytz.timezone(tz_name)
    except Exception:
        import pytz
        tz = pytz.UTC

    now = datetime.now(tz)
    run_at = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if run_at <= now:
        run_at += timedelta(days=1)

    chat_id = message.chat.id

    async def play_at_time():
        delay = (run_at - datetime.now(tz)).total_seconds()
        if delay > 0:
            await asyncio.sleep(delay)
        from bot import cache
        from helpers.downloader import resolve_to_youtube
        from plugins.play import _start_stream_from_track
        track = await resolve_to_youtube(query)
        if not track:
            return
        if await cache.is_stream_active(chat_id):
            await cache.add_to_queue(chat_id, track)
        else:
            await _start_stream_from_track(client, chat_id, track)
        try:
            await client.send_message(chat_id, f"<b>Scheduled play:</b> {sanitize_html(track['title'])}")
        except Exception:
            pass

    asyncio.create_task(play_at_time())
    await message.reply(SCHEDULE_SET.format(query=sanitize_html(query), time=time_str))


@Client.on_message(filters.command("alarm") & filters.private)
@anti_flood
async def alarm_command(client: Client, message: Message):
    args = message.command[1:]
    if len(args) < 1:
        await message.reply("<b>Usage:</b> <code>/alarm HH:MM [message]</code>")
        return

    time_str = args[0]
    alarm_msg = " ".join(args[1:]) if len(args) > 1 else "Wake up!"

    try:
        hour, minute = map(int, time_str.split(":"))
    except ValueError:
        await message.reply("<b>Invalid time format. Use HH:MM</b>")
        return

    now = datetime.now(timezone.utc)
    run_at = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if run_at <= now:
        run_at += timedelta(days=1)

    user_id = message.from_user.id

    async def send_alarm():
        delay = (run_at - datetime.now(timezone.utc)).total_seconds()
        if delay > 0:
            await asyncio.sleep(delay)
        try:
            await client.send_message(user_id, f"⏰ <b>Alarm!</b>\n{sanitize_html(alarm_msg)}")
        except Exception:
            pass

    asyncio.create_task(send_alarm())
    await message.reply(ALARM_SET.format(time=time_str))


@Client.on_message(filters.command("settimezone") & (filters.group | filters.channel))
@is_admin
async def settimezone_command(client: Client, message: Message):
    from bot import db
    args = message.command[1:]
    if not args:
        tz = await db.get_chat_timezone(message.chat.id)
        await message.reply(f"<b>Current timezone:</b> {tz}\nUsage: <code>/settimezone [timezone]</code>\nExample: <code>/settimezone Asia/Kolkata</code>")
        return

    tz_name = args[0]
    try:
        import pytz
        pytz.timezone(tz_name)
    except Exception:
        await message.reply(f"<b>Invalid timezone:</b> <code>{sanitize_html(tz_name)}</code>")
        return

    await db.set_chat_timezone(message.chat.id, tz_name)
    await message.reply(f"<b>Timezone set to:</b> <code>{sanitize_html(tz_name)}</code>")
