import json

from aiohttp import web
from loguru import logger
from pyrogram import Client, filters
from pyrogram.types import Message


async def handle_nowplaying(request: web.Request) -> web.Response:
    from bot import cache
    # chat_id comes as query param
    chat_id = request.rel_url.query.get("chat_id")
    if not chat_id:
        return web.json_response({"error": "Missing chat_id"}, status=400)
    try:
        np = await cache.get_now_playing(int(chat_id))
        volume = await cache.get_volume(int(chat_id))
        loop = await cache.get_loop(int(chat_id))
        effect = await cache.get_effect(int(chat_id))
        is_active = await cache.is_stream_active(int(chat_id))
        return web.json_response({
            "now_playing": np,
            "volume": volume,
            "loop": loop,
            "effect": effect,
            "is_active": is_active,
        })
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


async def handle_queue(request: web.Request) -> web.Response:
    from bot import cache
    chat_id = request.rel_url.query.get("chat_id")
    if not chat_id:
        return web.json_response({"error": "Missing chat_id"}, status=400)
    try:
        queue = await cache.get_queue(int(chat_id))
        return web.json_response({"queue": queue, "count": len(queue)})
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


async def handle_action(request: web.Request) -> web.Response:
    from bot import assistant_manager, cache
    try:
        body = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)

    action = body.get("action")
    chat_id = body.get("chat_id")
    if not action or not chat_id:
        return web.json_response({"error": "Missing action or chat_id"}, status=400)

    try:
        chat_id = int(chat_id)
        if action == "pause":
            await assistant_manager.pause(chat_id)
        elif action == "resume":
            await assistant_manager.resume(chat_id)
        elif action == "skip":
            from pyrogram import Client as PyroClient
            from bot import bot
            from plugins.play import _play_next
            await _play_next(bot, chat_id)
        elif action == "volume":
            vol = int(body.get("volume", 100))
            await cache.set_volume(chat_id, vol)
            await assistant_manager.change_volume(chat_id, vol)
        elif action == "effect":
            effect = body.get("effect", "Normal")
            await cache.set_effect(chat_id, effect)
        elif action == "loop":
            mode = body.get("mode", "off")
            await cache.set_loop(chat_id, mode)
        else:
            return web.json_response({"error": "Unknown action"}, status=400)
        return web.json_response({"ok": True})
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


def setup_webapp_routes(app: web.Application):
    app.router.add_get("/webapp/nowplaying", handle_nowplaying)
    app.router.add_get("/webapp/queue", handle_queue)
    app.router.add_post("/webapp/action", handle_action)


async def start_webapp_server():
    app = web.Application()
    setup_webapp_routes(app)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8080)
    await site.start()
    logger.info("WebApp server started on port 8080")
