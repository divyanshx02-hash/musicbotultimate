import re
from typing import Optional

import aiohttp
from loguru import logger


async def resolve_resso(url: str) -> Optional[dict]:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=aiohttp.ClientTimeout(total=10),
                allow_redirects=True,
            ) as resp:
                html = await resp.text()

        title = _extract_meta(html, "og:title") or ""
        description = _extract_meta(html, "og:description") or ""
        image = _extract_meta(html, "og:image") or ""

        parts = title.split(" - ", 1)
        song = parts[0].strip() if parts else title
        artist = parts[1].strip() if len(parts) > 1 else ""

        return {
            "title": song,
            "artist": artist,
            "thumbnail": image,
            "platform": "resso",
            "search_query": f"{song} {artist}",
        }
    except Exception as e:
        logger.error(f"Resso resolve error: {e}")
    return None


def _extract_meta(html: str, prop: str) -> Optional[str]:
    match = re.search(rf'<meta[^>]+property="{re.escape(prop)}"[^>]+content="([^"]+)"', html)
    return match.group(1) if match else None
