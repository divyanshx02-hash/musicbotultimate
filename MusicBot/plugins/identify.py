import os

from pyrogram import Client, filters
from pyrogram.types import Message

from helpers.decorators import anti_flood
from helpers.recognition import identify_song
from helpers.utils import clean_file, sanitize_html
from strings.buttons import identify_result_keyboard
from strings.messages import IDENTIFIED, IDENTIFY_FAILED, IDENTIFYING


@Client.on_message(filters.command("identify") & (filters.group | filters.private))
@anti_flood
async def identify_command(client: Client, message: Message):
    if not message.reply_to_message:
        await message.reply("<b>Reply to an audio/voice message to identify the song.</b>")
        return
    await _do_identify(client, message, message.reply_to_message)


@Client.on_message(
    (filters.audio | filters.voice | filters.document) & filters.private
)
async def auto_identify(client: Client, message: Message):
    # Auto-identify audio sent in PM
    await _do_identify(client, message, message)


async def _do_identify(client: Client, message: Message, target_message: Message):
    audio = (
        target_message.audio
        or target_message.voice
        or (target_message.document if target_message.document and target_message.document.mime_type and "audio" in target_message.document.mime_type else None)
    )
    if not audio:
        if message != target_message:
            await message.reply("<b>No audio found in that message.</b>")
        return

    msg = await message.reply(IDENTIFYING)
    path = None
    try:
        path = await client.download_media(
            target_message,
            file_name=f"downloads/identify_{audio.file_unique_id}.ogg",
        )
        result = await identify_song(path)
        if not result:
            await msg.edit(IDENTIFY_FAILED)
            return

        text = IDENTIFIED.format(
            title=sanitize_html(result.get("title", "Unknown")),
            artist=sanitize_html(result.get("artist", "Unknown")),
            album=sanitize_html(result.get("album", "N/A")),
            release_date=result.get("release_date", "N/A"),
            score=result.get("score", 0),
            source=result.get("source", ""),
        )
        chat_id = message.chat.id
        kb = identify_result_keyboard(result["title"], result.get("artist", ""), chat_id)
        await msg.edit(text, reply_markup=kb)
    except Exception as e:
        await msg.edit(f"<b>Error during identification:</b> <code>{e}</code>")
    finally:
        if path:
            clean_file(path)
