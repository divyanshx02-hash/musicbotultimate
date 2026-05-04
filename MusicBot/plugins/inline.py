from pyrogram import Client
from pyrogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InlineQuery,
    InlineQueryResultArticle,
    InputTextMessageContent,
)

from helpers.downloader import search_youtube
from helpers.utils import format_duration, sanitize_html


@Client.on_inline_query()
async def inline_search(client: Client, query: InlineQuery):
    text = query.query.strip()
    if not text:
        await query.answer(
            results=[
                InlineQueryResultArticle(
                    title="Search for a song",
                    input_message_content=InputTextMessageContent("Type a song name to search."),
                    description="Type a song name...",
                )
            ],
            cache_time=0,
        )
        return

    results_raw = await search_youtube(text, limit=5)
    if not results_raw:
        await query.answer(
            results=[
                InlineQueryResultArticle(
                    title="No results found",
                    input_message_content=InputTextMessageContent(f"No results for: {text}"),
                    description="Try a different search",
                )
            ],
            cache_time=10,
        )
        return

    results = []
    for r in results_raw:
        vid = r.get("id", "")
        title = r.get("title", "Unknown")
        uploader = r.get("uploader", "")
        duration = format_duration(r.get("duration") or 0)
        url = f"https://www.youtube.com/watch?v={vid}"
        thumb = r.get("thumbnail", "")

        results.append(
            InlineQueryResultArticle(
                title=title[:100],
                input_message_content=InputTextMessageContent(
                    f"<b>{sanitize_html(title)}</b>\n<i>{sanitize_html(uploader)}</i>\nDuration: {duration}\n\n{url}"
                ),
                description=f"{uploader} • {duration}",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("▶️ Play", url=f"https://t.me/your_bot?start=play_{vid}"),
                    InlineKeyboardButton("🔗 YouTube", url=url),
                ]]),
            )
        )

    await query.answer(results=results, cache_time=30)
