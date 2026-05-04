from pyrogram import Client, filters
from pyrogram.types import ChatPermissions, Message

from helpers.decorators import is_admin
from helpers.utils import sanitize_html
from strings.messages import (
    AUTO_KICKED,
    BANNED,
    KICKED,
    MUTED,
    RULES_SET,
    UNBANNED,
    UNMUTED,
    WARNED,
    WELCOME_SET,
)


async def _get_target(message: Message) -> tuple:
    if message.reply_to_message and message.reply_to_message.from_user:
        u = message.reply_to_message.from_user
        return u.id, u.first_name
    if len(message.command) > 1:
        username_or_id = message.command[1]
        try:
            user = await message._client.get_users(username_or_id)
            return user.id, user.first_name
        except Exception:
            pass
    return None, None


@Client.on_message(filters.command("ban") & (filters.group | filters.channel))
@is_admin
async def ban_command(client: Client, message: Message):
    user_id, name = await _get_target(message)
    if not user_id:
        await message.reply("<b>Reply to a user or provide username.</b>")
        return
    await client.ban_chat_member(message.chat.id, user_id)
    await message.reply(BANNED.format(user=sanitize_html(name or str(user_id))))


@Client.on_message(filters.command("unban") & (filters.group | filters.channel))
@is_admin
async def unban_command(client: Client, message: Message):
    user_id, name = await _get_target(message)
    if not user_id:
        await message.reply("<b>Reply to a user or provide username.</b>")
        return
    await client.unban_chat_member(message.chat.id, user_id)
    await message.reply(UNBANNED.format(user=sanitize_html(name or str(user_id))))


@Client.on_message(filters.command("kick") & (filters.group | filters.channel))
@is_admin
async def kick_command(client: Client, message: Message):
    user_id, name = await _get_target(message)
    if not user_id:
        await message.reply("<b>Reply to a user or provide username.</b>")
        return
    await client.ban_chat_member(message.chat.id, user_id)
    await client.unban_chat_member(message.chat.id, user_id)
    await message.reply(KICKED.format(user=sanitize_html(name or str(user_id))))


@Client.on_message(filters.command("mute") & (filters.group | filters.channel))
@is_admin
async def mute_command(client: Client, message: Message):
    user_id, name = await _get_target(message)
    if not user_id:
        await message.reply("<b>Reply to a user or provide username.</b>")
        return
    await client.restrict_chat_member(
        message.chat.id,
        user_id,
        ChatPermissions(can_send_messages=False),
    )
    await message.reply(MUTED.format(user=sanitize_html(name or str(user_id))))


@Client.on_message(filters.command("unmute") & (filters.group | filters.channel))
@is_admin
async def unmute_command(client: Client, message: Message):
    user_id, name = await _get_target(message)
    if not user_id:
        await message.reply("<b>Reply to a user or provide username.</b>")
        return
    await client.restrict_chat_member(
        message.chat.id,
        user_id,
        ChatPermissions(
            can_send_messages=True,
            can_send_media_messages=True,
            can_send_other_messages=True,
            can_add_web_page_previews=True,
        ),
    )
    await message.reply(UNMUTED.format(user=sanitize_html(name or str(user_id))))


@Client.on_message(filters.command("warn") & (filters.group | filters.channel))
@is_admin
async def warn_command(client: Client, message: Message):
    from bot import db
    user_id, name = await _get_target(message)
    if not user_id:
        await message.reply("<b>Reply to a user or provide username.</b>")
        return

    reason = " ".join(message.command[2:]) if len(message.command) > 2 else "No reason provided"
    count = await db.add_warn(message.chat.id, user_id, reason)
    await message.reply(WARNED.format(
        user=sanitize_html(name or str(user_id)),
        count=count,
        reason=sanitize_html(reason),
    ))

    if count >= 3:
        try:
            await client.ban_chat_member(message.chat.id, user_id)
            await client.unban_chat_member(message.chat.id, user_id)
            await message.reply(AUTO_KICKED.format(user=sanitize_html(name or str(user_id))))
        except Exception:
            pass


@Client.on_message(filters.command("warns") & (filters.group | filters.channel))
@is_admin
async def warns_command(client: Client, message: Message):
    from bot import db
    user_id, name = await _get_target(message)
    if not user_id:
        await message.reply("<b>Reply to a user or provide username.</b>")
        return

    warns = await db.get_warns(message.chat.id, user_id)
    if not warns:
        await message.reply(f"<b>{sanitize_html(name or str(user_id))}</b> has no warnings.")
        return

    lines = [f"<b>Warnings for {sanitize_html(name or str(user_id))}:</b>\n"]
    for i, w in enumerate(warns, 1):
        lines.append(f"{i}. {sanitize_html(w.get('reason', 'No reason'))}")
    await message.reply("\n".join(lines))


@Client.on_message(filters.command("resetwarn") & (filters.group | filters.channel))
@is_admin
async def resetwarn_command(client: Client, message: Message):
    from bot import db
    user_id, name = await _get_target(message)
    if not user_id:
        await message.reply("<b>Reply to a user or provide username.</b>")
        return
    await db.reset_warns(message.chat.id, user_id)
    await message.reply(f"<b>Warnings reset for {sanitize_html(name or str(user_id))}.</b>")


@Client.on_message(filters.command("purge") & (filters.group | filters.channel))
@is_admin
async def purge_command(client: Client, message: Message):
    args = message.command[1:]
    count = int(args[0]) if args and args[0].isdigit() else 10
    count = min(count, 200)

    deleted = 0
    async for msg in client.get_chat_history(message.chat.id, limit=count + 1):
        try:
            await msg.delete()
            deleted += 1
        except Exception:
            pass
    notify = await message.reply(f"<b>Deleted {deleted} messages.</b>")
    import asyncio
    await asyncio.sleep(3)
    try:
        await notify.delete()
    except Exception:
        pass


@Client.on_message(filters.command("pin") & (filters.group | filters.channel))
@is_admin
async def pin_command(client: Client, message: Message):
    if not message.reply_to_message:
        await message.reply("<b>Reply to a message to pin it.</b>")
        return
    await message.reply_to_message.pin()
    await message.reply("<b>Message pinned.</b>")


@Client.on_message(filters.command("unpin") & (filters.group | filters.channel))
@is_admin
async def unpin_command(client: Client, message: Message):
    await client.unpin_all_chat_messages(message.chat.id)
    await message.reply("<b>All messages unpinned.</b>")


@Client.on_message(filters.command("setwelcome") & (filters.group | filters.channel))
@is_admin
async def setwelcome_command(client: Client, message: Message):
    from bot import db
    text = " ".join(message.command[1:])
    if not text:
        await message.reply("<b>Usage:</b> <code>/setwelcome [text]</code>\nPlaceholders: {mention} {name} {chat}</code>")
        return
    await db.set_welcome(message.chat.id, text)
    await message.reply(WELCOME_SET)


@Client.on_message(filters.command("setrules") & (filters.group | filters.channel))
@is_admin
async def setrules_command(client: Client, message: Message):
    from bot import db
    text = " ".join(message.command[1:])
    if not text:
        await message.reply("<b>Usage:</b> <code>/setrules [text]</code>")
        return
    await db.set_rules(message.chat.id, text)
    await message.reply(RULES_SET)


@Client.on_message(filters.command("rules") & (filters.group | filters.channel))
async def rules_command(client: Client, message: Message):
    from bot import db
    rules = await db.get_rules(message.chat.id)
    if rules:
        await message.reply(f"<b>Group Rules:</b>\n\n{sanitize_html(rules)}")
    else:
        await message.reply("<b>No rules set.</b> Admins can set rules with /setrules.")


@Client.on_message(filters.new_chat_members)
async def welcome_handler(client: Client, message: Message):
    from bot import db
    welcome = await db.get_welcome(message.chat.id)
    if not welcome:
        return
    for member in message.new_chat_members:
        if member.is_bot:
            continue
        try:
            mention = f'<a href="tg://user?id={member.id}">{sanitize_html(member.first_name)}</a>'
            text = welcome.replace("{mention}", mention).replace("{name}", sanitize_html(member.first_name)).replace("{chat}", sanitize_html(message.chat.title or "this group"))
            await message.reply(text)
        except Exception:
            pass
