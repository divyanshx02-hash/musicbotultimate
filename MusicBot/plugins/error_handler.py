"""Global error handler for unhandled Pyrogram exceptions."""
from loguru import logger
from pyrogram import Client
from pyrogram.errors import FloodWait


@Client.on_message()
async def _global_error_catcher(client: Client, message):
    """No-op catch-all — actual error handling is per-handler."""
    pass


async def handle_error(client: Client, exception: Exception, message=None):
    """Central error handler — call from try/except blocks in handlers."""
    logger.error(f"Unhandled exception: {exception}", exc_info=True)

    if isinstance(exception, FloodWait):
        logger.warning(f"FloodWait: sleeping {exception.value}s")
        import asyncio
        await asyncio.sleep(exception.value)
        return

    from config import LOGGER_ID
    if LOGGER_ID and message:
        try:
            chat_info = f"Chat: {message.chat.id}" if message.chat else "Unknown chat"
            user_info = f"User: {message.from_user.id}" if message.from_user else "Unknown user"
            text = f"<b>Error</b>\n{chat_info}\n{user_info}\n<code>{str(exception)[:500]}</code>"
            await client.send_message(LOGGER_ID, text)
        except Exception:
            pass
