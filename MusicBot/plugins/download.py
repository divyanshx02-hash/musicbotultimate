import io
import os

from pyrogram import Client, filters
from pyrogram.types import Message

from helpers.decorators import anti_flood
from helpers.downloader import get_audio_stream_url, get_info
from helpers.utils import clean_file, format_duration, sanitize_html
from config import DOWNLOAD_DIR, TG_AUDIO_FILESIZE_LIMIT


@Client.on_message(filters.command("download") & (filters.group | filters.private))
@anti_flood
async def download_command(client: Client, message: Message):
    from bot import cache

    query = " ".join(message.command[1:]) if len(message.command) > 1 else ""

    if not query:
        # Download currently playing song
        chat_id = message.chat.id if message.chat.type.name != "PRIVATE" else 0
        if chat_id:
            np = await cache.get_now_playing(chat_id)
            if np:
                await _download_and_send(client, message, np)
                return
        await message.reply("<b>Usage:</b> <code>/download [song name or URL]</code>")
        return

    msg = await message.reply(f"<b>Searching:</b> <code>{sanitize_html(query[:60])}</code>")

    from helpers.downloader import search_youtube, is_valid_url
    if is_valid_url(query):
        info = await get_info(query)
        url = query
    else:
        results = await search_youtube(query, limit=1)
        if not results:
            await msg.edit("<b>No results found.</b>")
            return
        r = results[0]
        url = f"https://www.youtube.com/watch?v={r.get('id', '')}"
        info = r

    if not info:
        await msg.edit("<b>Could not get track info.</b>")
        return

    track = {
        "title": info.get("title", "Unknown"),
        "artist": info.get("uploader", ""),
        "duration": info.get("duration", 0),
        "url": url,
        "video_id": info.get("id", url),
    }
    await msg.delete()
    await _download_and_send(client, message, track)


async def _download_and_send(client: Client, message: Message, track: dict):
    import asyncio
    import subprocess

    msg = await message.reply(f"⏳ <b>Downloading:</b> <code>{sanitize_html(track.get('title', 'Unknown')[:50])}</code>")

    url = track.get("url", "")
    if not url:
        await msg.edit("<b>No downloadable URL.</b>")
        return

    output_path = os.path.join(DOWNLOAD_DIR, f"dl_{os.urandom(4).hex()}.mp3")

    try:
        from config import COOKIES_FILE
        args = ["yt-dlp", "--no-warnings", "--quiet", "-x", "--audio-format", "mp3", "--audio-quality", "0"]
        if os.path.exists(COOKIES_FILE):
            args += ["--cookies", COOKIES_FILE]
        args += ["-o", output_path, url]

        proc = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)

        if not os.path.exists(output_path):
            await msg.edit(f"<b>Download failed.</b>")
            return

        file_size = os.path.getsize(output_path)
        if file_size > TG_AUDIO_FILESIZE_LIMIT:
            await msg.edit(f"<b>File too large to send ({file_size // 1024 // 1024}MB).</b>")
            clean_file(output_path)
            return

        await msg.edit("⬆️ <b>Uploading...</b>")
        await client.send_audio(
            message.chat.id,
            audio=output_path,
            title=track.get("title", "Unknown")[:64],
            performer=track.get("artist", "")[:64],
            duration=track.get("duration", 0),
            caption=f"<b>{sanitize_html(track.get('title', 'Unknown'))}</b>",
        )
        await msg.delete()
    except asyncio.TimeoutError:
        await msg.edit("<b>Download timed out.</b>")
    except Exception as e:
        await msg.edit(f"<b>Error:</b> <code>{e}</code>")
    finally:
        clean_file(output_path)
