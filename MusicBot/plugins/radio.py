from pyrogram import Client, filters
from pyrogram.types import Message

from helpers.decorators import anti_flood, is_admin
from helpers.utils import sanitize_html
from strings.buttons import radio_keyboard
from strings.messages import RADIO_LIST_HEADER, RADIO_PLAYING

DEFAULT_STATIONS = [
    {"name": "Chill Hits", "url": "https://streams.radiomast.io/radiomast_92914a29-4a68-4a44-b2df-2fd8a1450093", "genre": "Pop", "country": "US"},
    {"name": "Jazz FM", "url": "https://stream.jazzfm.com/stream", "genre": "Jazz", "country": "US"},
    {"name": "Classic Rock Radio", "url": "https://streams.classicrock-radio.com:8010/stream.mp3", "genre": "Rock", "country": "UK"},
    {"name": "Lofi Beats", "url": "https://streams.radiomast.io/radiomast_lofi", "genre": "Lofi", "country": "US"},
    {"name": "EDM Radio", "url": "https://streams.radiomast.io/radiomast_edm", "genre": "EDM", "country": "US"},
    {"name": "BBC World Service", "url": "https://stream.live.vc.bbcmedia.co.uk/bbc_world_service", "genre": "News", "country": "UK"},
    {"name": "Bollywood Hits", "url": "https://streams.radiomast.io/radiomast_bollywood", "genre": "Bollywood", "country": "IN"},
]


async def _ensure_default_stations():
    from bot import db
    existing = await db.get_radio_stations()
    if not existing:
        for s in DEFAULT_STATIONS:
            await db.add_radio_station(s)


@Client.on_message(filters.command(["radio", "radiolist"]) & (filters.group | filters.channel))
@anti_flood
async def radio_command(client: Client, message: Message):
    from bot import db
    await _ensure_default_stations()
    stations = await db.get_radio_stations()
    if not stations:
        await message.reply("<b>No radio stations available.</b> Admin can add with /addradio.")
        return

    chat_id = message.chat.id
    kb = radio_keyboard(stations, chat_id)
    await message.reply(RADIO_LIST_HEADER, reply_markup=kb)


@Client.on_message(filters.command("addradio") & (filters.group | filters.channel))
@is_admin
async def addradio_command(client: Client, message: Message):
    from bot import db
    args = " ".join(message.command[1:]).split("|")
    if len(args) < 2:
        await message.reply("<b>Usage:</b> <code>/addradio Name | Stream URL | Genre | Country</code>")
        return
    name = args[0].strip()
    url = args[1].strip()
    genre = args[2].strip() if len(args) > 2 else "Music"
    country = args[3].strip() if len(args) > 3 else ""
    await db.add_radio_station({"name": name, "url": url, "genre": genre, "country": country})
    await message.reply(f"<b>Radio station added:</b> {sanitize_html(name)}")


@Client.on_message(filters.command("delradio") & (filters.group | filters.channel))
@is_admin
async def delradio_command(client: Client, message: Message):
    from bot import db
    name = " ".join(message.command[1:])
    if not name:
        await message.reply("<b>Usage:</b> <code>/delradio [name]</code>")
        return
    await db.remove_radio_station(name)
    await message.reply(f"<b>Removed radio station:</b> {sanitize_html(name)}")


@Client.on_message(filters.command("live") & (filters.group | filters.channel))
@is_admin
async def live_command(client: Client, message: Message):
    from bot import assistant_manager, cache
    from helpers.downloader import get_audio_stream_url, get_info, is_valid_url

    args = " ".join(message.command[1:])
    if not args or not is_valid_url(args):
        await message.reply("<b>Usage:</b> <code>/live [YouTube Live URL]</code>")
        return

    msg = await message.reply("<b>Fetching live stream...</b>")
    info = await get_info(args)
    if not info:
        await msg.edit("<b>Could not fetch stream info.</b>")
        return

    stream_url = await get_audio_stream_url(args)
    if not stream_url:
        await msg.edit("<b>Could not get stream URL.</b>")
        return

    chat_id = message.chat.id
    track = {
        "title": info.get("title", "Live Stream"),
        "artist": info.get("uploader", ""),
        "url": args,
        "video_id": info.get("id", args),
        "platform": "youtube",
        "is_live": True,
    }

    if await cache.is_stream_active(chat_id):
        await cache.add_to_queue(chat_id, track)
        await msg.edit(f"<b>Live stream queued:</b> {sanitize_html(track['title'])}")
    else:
        ok = await assistant_manager.play_audio(chat_id, stream_url)
        if ok:
            await cache.set_now_playing(chat_id, track)
            await cache.set_stream_active(chat_id, True)
            await msg.edit(f"🔴 <b>Now Streaming Live:</b> {sanitize_html(track['title'])}")
        else:
            await msg.edit("<b>Could not start live stream.</b>")
