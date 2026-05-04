from pyrogram import Client, filters
from pyrogram.types import Message

from helpers.decorators import anti_flood, is_admin
from helpers.utils import format_duration, sanitize_html, split_pages
from strings.buttons import queue_keyboard
from strings.messages import (
    NO_ACTIVE_STREAM,
    QUEUE_CLEARED,
    QUEUE_EMPTY,
    QUEUE_HEADER,
    QUEUE_ITEM,
    QUEUE_SHUFFLED,
    REMOVED_FROM_QUEUE,
)


@Client.on_message(filters.command("queue") & (filters.group | filters.channel))
@anti_flood
async def queue_command(client: Client, message: Message):
    from bot import cache
    queue = await cache.get_queue(message.chat.id)
    if not queue:
        np = await cache.get_now_playing(message.chat.id)
        if np:
            await message.reply(f"<b>Queue:</b> 1 song playing\n\n🎵 <b>{sanitize_html(np.get('title', 'Unknown'))}</b>")
        else:
            await message.reply(QUEUE_EMPTY)
        return

    await _send_queue_page(client, message, queue, 0)


async def _send_queue_page(client, message, queue, page):
    pages = split_pages(queue, 5)
    if not pages:
        await message.reply(QUEUE_EMPTY)
        return
    page = max(0, min(page, len(pages) - 1))
    items = pages[page]
    chat_id = message.chat.id

    lines = [QUEUE_HEADER.format(count=len(queue))]
    offset = page * 5
    for i, track in enumerate(items):
        lines.append(QUEUE_ITEM.format(
            pos=offset + i + 1,
            title=sanitize_html(track.get("title", "Unknown")[:40]),
            artist=sanitize_html(track.get("artist", "")[:25]),
            duration=format_duration(track.get("duration") or 0),
            requester=sanitize_html(track.get("requester_name", "")[:20]),
        ))

    keyboard = queue_keyboard(chat_id, page, len(pages))
    await message.reply("\n".join(lines), reply_markup=keyboard)


@Client.on_message(filters.command("remove") & (filters.group | filters.channel))
@is_admin
async def remove_command(client: Client, message: Message):
    from bot import cache
    args = message.command
    if len(args) < 2 or not args[1].isdigit():
        await message.reply("<b>Usage:</b> <code>/remove [position]</code>")
        return

    pos = int(args[1]) - 1
    queue = await cache.get_queue(message.chat.id)
    if pos < 0 or pos >= len(queue):
        await message.reply("<b>Invalid position.</b>")
        return

    track = queue[pos]
    await cache.remove_from_queue(message.chat.id, pos)
    await message.reply(REMOVED_FROM_QUEUE.format(title=sanitize_html(track.get("title", "Unknown"))))


@Client.on_message(filters.command("move") & (filters.group | filters.channel))
@is_admin
async def move_command(client: Client, message: Message):
    from bot import cache
    args = message.command
    if len(args) < 3:
        await message.reply("<b>Usage:</b> <code>/move [from] [to]</code>")
        return
    try:
        from_pos = int(args[1]) - 1
        to_pos = int(args[2]) - 1
    except ValueError:
        await message.reply("<b>Please provide valid numbers.</b>")
        return

    ok = await cache.move_in_queue(message.chat.id, from_pos, to_pos)
    if ok:
        await message.reply(f"<b>Moved song from position {from_pos+1} to {to_pos+1}.</b>")
    else:
        await message.reply("<b>Invalid positions.</b>")


@Client.on_message(filters.command("skipto") & (filters.group | filters.channel))
@is_admin
async def skipto_command(client: Client, message: Message):
    from bot import cache
    args = message.command
    if len(args) < 2 or not args[1].isdigit():
        await message.reply("<b>Usage:</b> <code>/skipto [position]</code>")
        return

    pos = int(args[1]) - 1
    queue = await cache.get_queue(message.chat.id)
    if pos <= 0 or pos >= len(queue):
        await message.reply("<b>Invalid position.</b>")
        return

    # Remove songs before position
    queue = queue[pos:]
    await cache.set_queue(message.chat.id, queue)

    from plugins.play import _play_next
    await _play_next(client, message.chat.id)
    await message.reply(f"<b>Skipping to position {pos + 1}...</b>")


@Client.on_message(filters.command("shuffle") & (filters.group | filters.channel))
@is_admin
async def shuffle_command(client: Client, message: Message):
    from bot import cache
    await cache.shuffle_queue(message.chat.id)
    await message.reply(QUEUE_SHUFFLED)


@Client.on_message(filters.command("clearqueue") & (filters.group | filters.channel))
@is_admin
async def clearqueue_command(client: Client, message: Message):
    from bot import cache
    await cache.clear_queue(message.chat.id)
    await message.reply(QUEUE_CLEARED)


@Client.on_message(filters.command("openqueue") & (filters.group | filters.channel))
@is_admin
async def openqueue_command(client: Client, message: Message):
    from bot import db
    args = message.command
    chat_id = message.chat.id
    if len(args) > 1:
        state = args[1].lower() == "on"
        await db.upsert_chat(chat_id, {"open_queue": state})
        status = "enabled" if state else "disabled"
    else:
        state = await db.toggle_open_queue(chat_id)
        status = "enabled" if state else "disabled"
    await message.reply(f"<b>Open queue {status}.</b> {'Anyone can add songs.' if state else 'Only admins can add songs.'}")
