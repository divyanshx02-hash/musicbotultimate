import io
from datetime import datetime, timezone

from pyrogram import Client, filters
from pyrogram.types import Message

from helpers.decorators import anti_flood
from helpers.thumbnail import generate_wrapped_card
from helpers.utils import sanitize_html
from strings.messages import WRAPPED_EMPTY, WRAPPED_LOADING


@Client.on_message(filters.command("wrapped") & (filters.group | filters.private))
@anti_flood
async def wrapped_command(client: Client, message: Message):
    from bot import db

    args = message.command[1:]
    year = int(args[0]) if args and args[0].isdigit() else datetime.now(timezone.utc).year

    msg = await message.reply(WRAPPED_LOADING)

    user_id = message.from_user.id if message.from_user else 0
    stats = await db.get_user_wrapped(user_id, year)

    if not stats:
        await msg.edit(WRAPPED_EMPTY.format(year=year))
        return

    name = message.from_user.first_name if message.from_user else "User"
    img = await generate_wrapped_card(stats, name, year)

    if img:
        await msg.delete()
        await client.send_photo(
            message.chat.id,
            photo=io.BytesIO(img),
            caption=(
                f"<b>{sanitize_html(name)}'s {year} Music Wrapped</b>\n\n"
                f"🎵 Songs Played: <b>{stats.get('total_songs', 0)}</b>\n"
                f"🎤 Top Song: <b>{sanitize_html(stats.get('top_song', 'Unknown'))}</b>\n"
                f"👤 Top Artist: <b>{sanitize_html(stats.get('top_artist', 'Unknown'))}</b>\n"
                f"🔥 Best Streak: <b>{stats.get('streak', 0)} days</b>"
            ),
        )
    else:
        await msg.edit(
            f"<b>{sanitize_html(name)}'s {year} Music Wrapped</b>\n\n"
            f"Songs Played: {stats.get('total_songs', 0)}\n"
            f"Top Song: {sanitize_html(stats.get('top_song', 'Unknown'))}\n"
            f"Top Artist: {sanitize_html(stats.get('top_artist', 'Unknown'))}\n"
            f"Best Streak: {stats.get('streak', 0)} days"
        )


@Client.on_message(filters.command("groupwrapped") & (filters.group | filters.channel))
@anti_flood
async def groupwrapped_command(client: Client, message: Message):
    from bot import db

    args = message.command[1:]
    year = int(args[0]) if args and args[0].isdigit() else datetime.now(timezone.utc).year

    msg = await message.reply(WRAPPED_LOADING)

    chat_id = message.chat.id
    stats = await db.get_chat_wrapped(chat_id, year)

    if not stats:
        await msg.edit(WRAPPED_EMPTY.format(year=year))
        return

    chat_title = message.chat.title or "This Group"
    img = await generate_wrapped_card(stats, chat_title, year)

    if img:
        await msg.delete()
        await client.send_photo(
            chat_id,
            photo=io.BytesIO(img),
            caption=(
                f"<b>{sanitize_html(chat_title)} — {year} Music Wrapped</b>\n\n"
                f"🎵 Songs Played: <b>{stats.get('total_songs', 0)}</b>\n"
                f"🎤 Top Song: <b>{sanitize_html(stats.get('top_song', 'Unknown'))}</b>\n"
                f"👤 Top Artist: <b>{sanitize_html(stats.get('top_artist', 'Unknown'))}</b>\n"
                f"🔥 Best Streak: <b>{stats.get('streak', 0)} days</b>"
            ),
        )
    else:
        await msg.edit(
            f"<b>{sanitize_html(chat_title)} — {year} Music Wrapped</b>\n\n"
            f"Songs Played: {stats.get('total_songs', 0)}\n"
            f"Top Song: {sanitize_html(stats.get('top_song', 'Unknown'))}"
        )
