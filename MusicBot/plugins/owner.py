import time

from pyrogram import Client, filters
from pyrogram.types import Message

from helpers.decorators import is_owner, is_sudo
from helpers.utils import sanitize_html


@Client.on_message(filters.command("broadcast") & filters.private)
@is_owner
async def broadcast_command(client: Client, message: Message):
    from bot import db
    text = " ".join(message.command[1:])
    if not text and not message.reply_to_message:
        await message.reply("<b>Usage:</b> <code>/broadcast [message]</code> or reply to a message")
        return

    broadcast_text = text or message.reply_to_message.text or ""
    if not broadcast_text:
        await message.reply("<b>No text to broadcast.</b>")
        return

    msg = await message.reply("<b>Broadcasting...</b>")
    chats = await db.get_all_chats()
    sent = 0
    failed = 0
    for chat in chats:
        try:
            await client.send_message(chat["chat_id"], broadcast_text)
            sent += 1
        except Exception:
            failed += 1

    from strings.messages import BROADCAST_DONE
    await msg.edit(BROADCAST_DONE.format(count=sent) + f"\nFailed: {failed}")


@Client.on_message(filters.command("gban") & filters.private)
@is_sudo
async def gban_command(client: Client, message: Message):
    from bot import db
    args = message.command[1:]
    if not args:
        await message.reply("<b>Usage:</b> <code>/gban [user_id] [reason]</code>")
        return
    try:
        user_id = int(args[0])
    except ValueError:
        await message.reply("<b>Invalid user ID.</b>")
        return
    reason = " ".join(args[1:]) if len(args) > 1 else "No reason"
    await db.gban_user(user_id, reason)
    await message.reply(f"<b>Globally banned user:</b> <code>{user_id}</code>\nReason: {sanitize_html(reason)}")


@Client.on_message(filters.command("ungban") & filters.private)
@is_sudo
async def ungban_command(client: Client, message: Message):
    from bot import db
    args = message.command[1:]
    if not args:
        await message.reply("<b>Usage:</b> <code>/ungban [user_id]</code>")
        return
    try:
        user_id = int(args[0])
    except ValueError:
        await message.reply("<b>Invalid user ID.</b>")
        return
    await db.ungban_user(user_id)
    await message.reply(f"<b>Removed global ban for:</b> <code>{user_id}</code>")


@Client.on_message(filters.command("auth") & (filters.group | filters.channel))
@is_owner
async def auth_command(client: Client, message: Message):
    from bot import db
    args = message.command[1:]
    if not args:
        await message.reply("<b>Usage:</b> <code>/auth [user_id]</code>")
        return
    try:
        user_id = int(args[0])
    except ValueError:
        await message.reply("<b>Invalid user ID.</b>")
        return
    await db.add_sudo(user_id)
    await message.reply(f"<b>Granted sudo to:</b> <code>{user_id}</code>")


@Client.on_message(filters.command("unauth") & (filters.group | filters.channel))
@is_owner
async def unauth_command(client: Client, message: Message):
    from bot import db
    args = message.command[1:]
    if not args:
        await message.reply("<b>Usage:</b> <code>/unauth [user_id]</code>")
        return
    try:
        user_id = int(args[0])
    except ValueError:
        await message.reply("<b>Invalid user ID.</b>")
        return
    await db.remove_sudo(user_id)
    await message.reply(f"<b>Removed sudo from:</b> <code>{user_id}</code>")


@Client.on_message(filters.command("allowgc") & filters.private)
@is_owner
async def allowgc_command(client: Client, message: Message):
    from bot import db
    args = message.command[1:]
    if not args:
        await message.reply("<b>Usage:</b> <code>/allowgc [chat_id]</code>")
        return
    try:
        chat_id = int(args[0])
    except ValueError:
        await message.reply("<b>Invalid chat ID.</b>")
        return
    await db.allow_chat(chat_id)
    await message.reply(f"<b>Chat allowed:</b> <code>{chat_id}</code>")


@Client.on_message(filters.command("disallowgc") & filters.private)
@is_owner
async def disallowgc_command(client: Client, message: Message):
    from bot import db
    args = message.command[1:]
    if not args:
        await message.reply("<b>Usage:</b> <code>/disallowgc [chat_id]</code>")
        return
    try:
        chat_id = int(args[0])
    except ValueError:
        await message.reply("<b>Invalid chat ID.</b>")
        return
    await db.disallow_chat(chat_id)
    await message.reply(f"<b>Chat disallowed:</b> <code>{chat_id}</code>")


@Client.on_message(filters.command("block") & filters.private)
@is_sudo
async def block_command(client: Client, message: Message):
    from bot import db
    args = message.command[1:]
    if not args:
        await message.reply("<b>Usage:</b> <code>/block [user_id]</code>")
        return
    try:
        user_id = int(args[0])
    except ValueError:
        await message.reply("<b>Invalid user ID.</b>")
        return
    await db.block_user(user_id)
    await message.reply(f"<b>Blocked user:</b> <code>{user_id}</code>")


@Client.on_message(filters.command("unblock") & filters.private)
@is_sudo
async def unblock_command(client: Client, message: Message):
    from bot import db
    args = message.command[1:]
    if not args:
        await message.reply("<b>Usage:</b> <code>/unblock [user_id]</code>")
        return
    try:
        user_id = int(args[0])
    except ValueError:
        await message.reply("<b>Invalid user ID.</b>")
        return
    await db.unblock_user(user_id)
    await message.reply(f"<b>Unblocked user:</b> <code>{user_id}</code>")


@Client.on_message(filters.command("logs") & filters.private)
@is_owner
async def logs_command(client: Client, message: Message):
    import os
    log_file = "logs/bot.log"
    if os.path.exists(log_file):
        await client.send_document(message.chat.id, log_file, caption="<b>Bot Logs</b>")
    else:
        await message.reply("<b>No log file found.</b>")


@Client.on_message(filters.command("restart") & filters.private)
@is_owner
async def restart_command(client: Client, message: Message):
    await message.reply("<b>Restarting bot...</b>")
    import os, sys
    os.execv(sys.executable, [sys.executable] + sys.argv)


@Client.on_message(filters.command("maintenance") & filters.private)
@is_owner
async def maintenance_command(client: Client, message: Message):
    from bot import maintenance_mode
    import bot as bot_module
    args = message.command[1:]
    if args and args[0].lower() in ("on", "true", "1"):
        bot_module.maintenance_mode = True
        await message.reply("<b>Maintenance mode enabled.</b> Bot is now offline for non-owners.")
    elif args and args[0].lower() in ("off", "false", "0"):
        bot_module.maintenance_mode = False
        await message.reply("<b>Maintenance mode disabled.</b> Bot is back online.")
    else:
        status = "enabled" if bot_module.maintenance_mode else "disabled"
        await message.reply(f"<b>Maintenance mode is {status}.</b>\nUsage: <code>/maintenance [on/off]</code>")


@Client.on_message(filters.command("reload") & filters.private)
@is_owner
async def reload_command(client: Client, message: Message):
    import importlib
    from pathlib import Path
    plugin_dir = Path(__file__).parent
    reloaded = 0
    errors = 0
    for plugin_file in sorted(plugin_dir.glob("*.py")):
        module_name = f"plugins.{plugin_file.stem}"
        try:
            if module_name in sys.modules:
                importlib.reload(sys.modules[module_name])
            else:
                importlib.import_module(module_name)
            reloaded += 1
        except Exception as e:
            errors += 1
            await message.reply(f"<b>Error reloading {module_name}:</b> <code>{e}</code>")
    await message.reply(f"<b>Reloaded {reloaded} plugins.</b> Errors: {errors}")


@Client.on_message(filters.command("setlang") & (filters.group | filters.channel))
async def setlang_command(client: Client, message: Message):
    from bot import db
    args = message.command[1:]
    if not args:
        lang = await db.get_chat_lang(message.chat.id)
        await message.reply(f"<b>Current language:</b> {lang}\nAvailable: en, hi, es, ar, te, bn")
        return
    lang = args[0].lower()
    if lang not in ("en", "hi", "es", "ar", "te", "bn"):
        await message.reply("<b>Unsupported language.</b> Available: en, hi, es, ar, te, bn")
        return
    await db.set_chat_lang(message.chat.id, lang)
    await message.reply(f"<b>Language set to:</b> <code>{lang}</code>")
