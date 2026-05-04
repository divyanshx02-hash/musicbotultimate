from pyrogram import Client, filters
from pyrogram.types import Message

from helpers.decorators import anti_flood
from helpers.utils import sanitize_html, split_pages
from strings.buttons import favlist_keyboard
from strings.messages import ADDED_FAV, FAV_LIST_EMPTY, REMOVED_FAV


@Client.on_message(filters.command(["fav", "favourite", "like"]) & (filters.group | filters.channel))
@anti_flood
async def fav_command(client: Client, message: Message):
    from bot import cache, db
    np = await cache.get_now_playing(message.chat.id)
    if not np:
        await message.reply("<b>No song is currently playing.</b>")
        return

    user_id = message.from_user.id
    video_id = np.get("video_id", "")

    if await db.is_favourite(user_id, video_id):
        await db.remove_favourite(user_id, video_id)
        await message.reply(REMOVED_FAV.format(title=sanitize_html(np.get("title", "Unknown"))))
    else:
        await db.add_favourite(user_id, dict(np))
        await message.reply(ADDED_FAV.format(title=sanitize_html(np.get("title", "Unknown"))))


@Client.on_message(filters.command(["favlist", "favourites", "faves"]) & (filters.group | filters.private))
@anti_flood
async def favlist_command(client: Client, message: Message):
    from bot import db
    user_id = message.from_user.id
    favs = await db.get_favourites(user_id)
    if not favs:
        await message.reply(FAV_LIST_EMPTY)
        return

    pages = split_pages(favs, 8)
    kb = favlist_keyboard(pages[0], 0, len(pages), user_id)
    text = f"<b>Your Favourites — {len(favs)} songs</b>\n\nPage 1/{len(pages)}"
    await message.reply(text, reply_markup=kb)
