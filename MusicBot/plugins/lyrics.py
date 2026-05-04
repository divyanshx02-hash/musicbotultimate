from pyrogram import Client, filters
from pyrogram.types import Message

from helpers.decorators import anti_flood
from helpers.lyrics import get_lyrics, paginate_lyrics
from helpers.utils import sanitize_html
from strings.buttons import lyrics_keyboard
from strings.messages import LYRICS_HEADER, LYRICS_NOT_FOUND


@Client.on_message(filters.command("lyrics") & (filters.group | filters.private))
@anti_flood
async def lyrics_command(client: Client, message: Message):
    from bot import cache

    query = " ".join(message.command[1:]) if len(message.command) > 1 else ""

    if not query:
        # Use currently playing song
        chat_id = message.chat.id if message.chat.type.name != "PRIVATE" else None
        if chat_id:
            np = await cache.get_now_playing(chat_id)
            if np:
                query = np.get("title", "")
                artist = np.get("artist", "")
            else:
                await message.reply("<b>Usage:</b> <code>/lyrics [song name]</code>")
                return
        else:
            await message.reply("<b>Usage:</b> <code>/lyrics [song name]</code>")
            return
    else:
        artist = ""

    msg = await message.reply(f"<b>Searching lyrics for:</b> <code>{sanitize_html(query[:60])}</code>")

    result = await get_lyrics(query, artist)
    if not result:
        await msg.edit(LYRICS_NOT_FOUND.format(query=sanitize_html(query[:60])))
        return

    pages = paginate_lyrics(result["lyrics"])
    header = LYRICS_HEADER.format(
        title=sanitize_html(result["title"]),
        artist=sanitize_html(result["artist"]),
        source=result.get("source", ""),
    )

    chat_id = message.chat.id
    kb = lyrics_keyboard(0, len(pages), chat_id) if len(pages) > 1 else None

    await msg.edit(
        header + pages[0],
        reply_markup=kb,
        disable_web_page_preview=True,
    )
