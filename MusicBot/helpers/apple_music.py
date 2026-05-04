import re
from typing import Optional

import aiohttp
from loguru import logger


async def resolve_apple_music(url: str) -> Optional[dict]:
    try:
        # Apple Music embeds metadata in the page og tags
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status != 200:
                    return None
                html = await resp.text()

        title = _extract_meta(html, "og:title") or ""
        description = _extract_meta(html, "og:description") or ""
        image = _extract_meta(html, "og:image") or ""

        # Title format is usually "Song - Artist"
        parts = title.split(" - ", 1)
        if len(parts) == 2:
            song, artist = parts[0].strip(), parts[1].strip()
        else:
            song = title.strip()
            artist = description.split(" by ")[-1].strip() if " by " in description else ""

        if not song:
            return None

        return {
            "title": song,
            "artist": artist,
            "thumbnail": image,
            "platform": "apple",
            "search_query": f"{song} {artist}",
        }
    except Exception as e:
        logger.error(f"Apple Music resolve error: {e}")
    return None


def _extract_meta(html: str, prop: str) -> Optional[str]:
    match = re.search(rf'<meta[^>]+property="{re.escape(prop)}"[^>]+content="([^"]+)"', html)
    return match.group(1) if match else None
