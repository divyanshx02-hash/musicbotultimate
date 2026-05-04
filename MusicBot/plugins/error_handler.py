"""Global error handler for unhandled Pyrogram exceptions."""
from loguru import logger
from pyrogram import Client
from pyrogram.errors import FloodWait
from pyrogram.types import Message


@Client.on_raw()
async def raw_update_handler(client: Client, update, users, chats):
    pass  # Placeholder for raw update handling


# Global exception handler for message handlers
class ErrorHandler:
    @staticmethod
    async def handle(client: Client, exception: Exception, message: Message = None):
        logger.error(f"Unhandled exception: {exception}", exc_info=True)

        if isinstance(exception, FloodWait):
            logger.warning(f"FloodWait: sleeping {exception.value}s")
            import asyncio
            await asyncio.sleep(exception.value)
            return

        # Send error to log channel
        from config import LOGGER_ID
        if LOGGER_ID and message:
            try:
                chat_info = f"Chat: {message.chat.id}" if message.chat else "Unknown chat"
                user_info = f"User: {message.from_user.id}" if message.from_user else "Unknown user"
                text = f"<b>Error</b>\n{chat_info}\n{user_info}\n<code>{str(exception)[:500]}</code>"
                await client.send_message(LOGGER_ID, text)
            except Exception:
                pass
