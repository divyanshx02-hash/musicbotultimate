from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from strings.buttons import help_keyboard
from strings.messages import HELP_MUSIC, START_TEXT


@Client.on_message(filters.command("start") & filters.private)
async def start_private(client: Client, message: Message):
    await message.reply(
        START_TEXT,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Add to Group", url=f"https://t.me/{(await client.get_me()).username}?startgroup=start")],
            [InlineKeyboardButton("Help", callback_data="help|0")],
        ]),
    )


@Client.on_message(filters.command("start") & (filters.group | filters.channel))
async def start_group(client: Client, message: Message):
    await message.reply(
        "<b>MusicBot is ready!</b>\n\nUse /play [song] to start streaming music in voice chat.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Help", callback_data="help|0")]]),
    )


@Client.on_message(filters.command("help") & (filters.group | filters.private))
async def help_command(client: Client, message: Message):
    await message.reply(HELP_MUSIC, reply_markup=help_keyboard(0))
