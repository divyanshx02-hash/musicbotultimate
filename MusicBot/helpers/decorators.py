import functools
from typing import Callable

from pyrogram import Client
from pyrogram.types import Message, CallbackQuery

from config import OWNER_ID


def is_owner(func: Callable) -> Callable:
    @functools.wraps(func)
    async def wrapper(client: Client, message: Message, *args, **kwargs):
        if message.from_user and message.from_user.id in OWNER_ID:
            return await func(client, message, *args, **kwargs)
        await message.reply("<b>This command is restricted to the bot owner.</b>")
    return wrapper


def is_sudo(func: Callable) -> Callable:
    @functools.wraps(func)
    async def wrapper(client: Client, message: Message, *args, **kwargs):
        from bot import db
        user_id = message.from_user.id if message.from_user else 0
        if user_id in OWNER_ID or await db.is_sudo(user_id):
            return await func(client, message, *args, **kwargs)
        await message.reply("<b>This command requires sudo privileges.</b>")
    return wrapper


def is_admin(func: Callable) -> Callable:
    @functools.wraps(func)
    async def wrapper(client: Client, message: Message, *args, **kwargs):
        from bot import db
        user_id = message.from_user.id if message.from_user else 0
        if user_id in OWNER_ID or await db.is_sudo(user_id):
            return await func(client, message, *args, **kwargs)
        if message.chat.type.name in ("GROUP", "SUPERGROUP"):
            try:
                member = await client.get_chat_member(message.chat.id, user_id)
                from pyrogram.enums import ChatMemberStatus
                if member.status in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER):
                    return await func(client, message, *args, **kwargs)
            except Exception:
                pass
        await message.reply("<b>This command is for admins only.</b>")
    return wrapper


def anti_flood(func: Callable) -> Callable:
    @functools.wraps(func)
    async def wrapper(client: Client, message: Message, *args, **kwargs):
        from bot import cache
        user_id = message.from_user.id if message.from_user else 0
        if await cache.check_flood(user_id):
            return
        return await func(client, message, *args, **kwargs)
    return wrapper


def private_bot_check(func: Callable) -> Callable:
    @functools.wraps(func)
    async def wrapper(client: Client, message: Message, *args, **kwargs):
        from bot import db
        from config import PRIVATE_BOT_MODE
        if PRIVATE_BOT_MODE and message.chat.type.name in ("GROUP", "SUPERGROUP"):
            if not await db.is_chat_allowed(message.chat.id):
                await message.reply("<b>This bot is in private mode. Contact the owner to get access.</b>")
                return
        return await func(client, message, *args, **kwargs)
    return wrapper


def maintenance_check(func: Callable) -> Callable:
    """Blocks non-owner commands when maintenance mode is active."""
    @functools.wraps(func)
    async def wrapper(client: Client, message: Message, *args, **kwargs):
        from bot import maintenance_mode
        if maintenance_mode:
            user_id = message.from_user.id if message.from_user else 0
            if user_id not in OWNER_ID:
                await message.reply("<b>Bot is under maintenance. Please try again later.</b>")
                return
        return await func(client, message, *args, **kwargs)
    return wrapper
