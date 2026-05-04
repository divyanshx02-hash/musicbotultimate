from pyrogram import filters
from pyrogram.types import Message

from config import OWNER_ID


def owner_filter(_, __, message: Message) -> bool:
    return bool(message.from_user and message.from_user.id in OWNER_ID)


def sudo_filter(_, __, message: Message) -> bool:
    from bot import db
    import asyncio
    if not message.from_user:
        return False
    user_id = message.from_user.id
    if user_id in OWNER_ID:
        return True
    try:
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(db.is_sudo(user_id))
    except Exception:
        return False


owner = filters.create(owner_filter, "OwnerFilter")
sudo = filters.create(sudo_filter, "SudoFilter")
