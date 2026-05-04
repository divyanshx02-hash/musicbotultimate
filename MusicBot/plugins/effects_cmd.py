from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, Message

from helpers.decorators import anti_flood, is_admin
from helpers.effects import EFFECT_NAMES, effects_keyboard, get_filter
from strings.messages import EFFECT_SET, SELECT_EFFECT


@Client.on_message(filters.command("effect") & (filters.group | filters.channel))
@is_admin
async def effect_command(client: Client, message: Message):
    from bot import cache

    args = message.command[1:]
    chat_id = message.chat.id

    if not args:
        current = await cache.get_effect(chat_id)
        kb = effects_keyboard(current)
        await message.reply(SELECT_EFFECT, reply_markup=InlineKeyboardMarkup(kb))
        return

    effect_name = " ".join(args).title()
    if effect_name not in EFFECT_NAMES:
        effect_name = "Normal"

    await cache.set_effect(chat_id, effect_name)

    # Restart stream with new effect if active
    np = await cache.get_now_playing(chat_id)
    if np:
        from bot import assistant_manager
        from helpers.downloader import get_audio_stream_url
        stream_url = await get_audio_stream_url(np.get("url", ""))
        if stream_url:
            ffmpeg_filter = get_filter(effect_name)
            ffmpeg_args = ["-af", ffmpeg_filter] if ffmpeg_filter else []
            await assistant_manager.change_stream(chat_id, stream_url, ffmpeg_args)

    await message.reply(EFFECT_SET.format(effect=effect_name))


@Client.on_message(filters.command("effects") & (filters.group | filters.channel))
@is_admin
async def effects_list_command(client: Client, message: Message):
    from bot import cache
    current = await cache.get_effect(message.chat.id)
    kb = effects_keyboard(current)
    await message.reply(SELECT_EFFECT, reply_markup=InlineKeyboardMarkup(kb))
