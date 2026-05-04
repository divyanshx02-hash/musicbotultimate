import asyncio
import importlib
import os
import signal
import sys
from pathlib import Path

from loguru import logger
from pyrogram import Client, idle
from pyrogram.enums import ParseMode

from config import (
    API_HASH,
    API_ID,
    BOT_TOKEN,
    LOGGER_ID,
    STRING_SESSION,
    STRING_SESSION2,
    STRING_SESSION3,
)
from helpers.assistant import AssistantManager
from helpers.cache import RedisCache
from helpers.database import Database
from helpers.downloader import refresh_cookies
from helpers.scheduler import setup_scheduler

# Configure logging
logger.remove()
os.makedirs("logs", exist_ok=True)
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="INFO",
)
logger.add("logs/bot.log", rotation="10 MB", retention="7 days", level="DEBUG")

# Global instances
bot: Client = None
db: Database = None
cache: RedisCache = None
assistant_manager: AssistantManager = None
scheduler = None
maintenance_mode: bool = False
_start_time: float = 0

# Track background tasks for cleanup
_bg_tasks: set[asyncio.Task] = set()


def _create_bg_task(coro) -> asyncio.Task:
    """Create a supervised background task that logs exceptions."""
    task = asyncio.create_task(coro)
    _bg_tasks.add(task)
    task.add_done_callback(_bg_task_done)
    return task


def _bg_task_done(task: asyncio.Task):
    _bg_tasks.discard(task)
    if task.cancelled():
        return
    exc = task.exception()
    if exc:
        logger.error(f"Background task crashed: {exc}")


async def load_plugins(app: Client):
    plugin_dir = Path(__file__).parent / "plugins"
    loaded = 0
    for plugin_file in sorted(plugin_dir.glob("*.py")):
        module_name = f"plugins.{plugin_file.stem}"
        try:
            module = importlib.import_module(module_name)
            loaded += 1
            logger.info(f"Loaded plugin: {module_name}")
        except Exception as e:
            logger.error(f"Failed to load plugin {module_name}: {e}")
    logger.info(f"Total plugins loaded: {loaded}")


async def start_bot():
    global bot, db, cache, assistant_manager, scheduler, maintenance_mode, _start_time
    import time
    _start_time = time.monotonic()

    logger.info("Starting MusicBot...")

    # Initialize database with retry
    db = Database()
    for attempt in range(3):
        try:
            await db.connect()
            logger.info("MongoDB connected")
            break
        except Exception as e:
            logger.error(f"MongoDB connection attempt {attempt+1} failed: {e}")
            if attempt < 2:
                await asyncio.sleep(5)
            else:
                logger.critical("MongoDB connection failed after 3 attempts")
                raise

    # Initialize cache with retry
    cache = RedisCache()
    for attempt in range(3):
        try:
            await cache.connect()
            logger.info("Redis connected")
            break
        except Exception as e:
            logger.error(f"Redis connection attempt {attempt+1} failed: {e}")
            if attempt < 2:
                await asyncio.sleep(5)
            else:
                logger.critical("Redis connection failed after 3 attempts")
                raise

    # Refresh cookies on startup
    if STRING_SESSION:
        try:
            await refresh_cookies()
            logger.info("Cookies loaded")
        except Exception as e:
            logger.warning(f"Cookie load failed (non-fatal): {e}")

    # Build session list
    sessions = [s for s in [STRING_SESSION, STRING_SESSION2, STRING_SESSION3] if s]

    # Initialize assistant manager
    assistant_manager = AssistantManager(sessions, API_ID, API_HASH)
    await assistant_manager.start_all()
    logger.info(f"Started {len(sessions)} assistant(s)")

    # Initialize main bot client
    bot = Client(
        "MusicBot",
        api_id=API_ID,
        api_hash=API_HASH,
        bot_token=BOT_TOKEN,
        parse_mode=ParseMode.HTML,
        plugins={"root": "plugins"},
        workdir=str(Path(__file__).parent),
    )

    # Setup APScheduler
    scheduler = await setup_scheduler(db)
    scheduler.start()
    logger.info("Scheduler started")

    # Start webapp server for Mini App backend
    try:
        from plugins.webapp import start_webapp_server
        _create_bg_task(start_webapp_server())
        logger.info("WebApp server starting on port 8080")
    except Exception as e:
        logger.warning(f"WebApp server failed to start: {e}")

    # Register stream end handlers on all assistants
    _register_stream_end_handlers()

    async with bot:
        me = await bot.get_me()
        logger.info(f"Bot started: @{me.username} ({me.id})")

        # Send startup log
        if LOGGER_ID:
            try:
                await bot.send_message(
                    LOGGER_ID,
                    f"<b>Bot Started</b>\n"
                    f"Name: <code>{me.first_name}</code>\n"
                    f"Username: @{me.username}\n"
                    f"Assistants: {len(sessions)}",
                )
            except Exception:
                pass

        # Start background tasks
        _create_bg_task(cookie_refresh_loop())
        _create_bg_task(assistant_manager.health_check_loop())

        # Graceful shutdown on signal
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, lambda: _create_bg_task(shutdown()))
            except NotImplementedError:
                pass  # Windows doesn't support add_signal_handler

        await idle()

    # Cleanup
    await _cleanup()


def _register_stream_end_handlers():
    """Register stream end callbacks on all assistant pytgcalls instances."""
    from pytgcalls.types.input_stream import StreamEndedUpdate

    async def on_stream_end(client, update):
        try:
            chat_id = update.chat_id
            logger.info(f"Stream ended in chat {chat_id}")
            from plugins.play import _play_next
            await _play_next(bot, chat_id)
        except Exception as e:
            logger.error(f"Stream end handler error: {e}")

    for assistant in assistant_manager.assistants:
        try:
            assistant.call.on_stream_end()(on_stream_end)
            logger.debug(f"Registered stream end handler on assistant {assistant.index}")
        except Exception as e:
            logger.error(f"Failed to register stream end handler: {e}")


async def shutdown():
    """Graceful shutdown handler."""
    logger.info("Shutdown signal received...")
    await _cleanup()
    # Stop the event loop
    loop = asyncio.get_running_loop()
    loop.stop()


async def _cleanup():
    global scheduler
    logger.info("Cleaning up...")

    # Cancel background tasks
    for task in _bg_tasks:
        task.cancel()
    for task in _bg_tasks:
        try:
            await task
        except asyncio.CancelledError:
            pass

    if scheduler:
        try:
            scheduler.shutdown(wait=False)
        except Exception:
            pass

    if assistant_manager:
        await assistant_manager.stop_all()

    if db:
        await db.close()

    if cache:
        await cache.close()

    logger.info("Bot stopped gracefully")


async def cookie_refresh_loop():
    from config import COOKIE_REFRESH_INTERVAL
    while True:
        await asyncio.sleep(COOKIE_REFRESH_INTERVAL)
        try:
            await refresh_cookies()
            logger.info("Cookies refreshed")
        except Exception as e:
            logger.error(f"Cookie refresh failed: {e}")


def main():
    asyncio.run(start_bot())


if __name__ == "__main__":
    main()
