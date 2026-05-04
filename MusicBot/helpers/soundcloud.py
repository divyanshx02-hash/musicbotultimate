from typing import Optional

from helpers.downloader import get_info, search_youtube


async def resolve_soundcloud(url: str) -> Optional[dict]:
    info = await get_info(url)
    if not info:
        return None
    return {
        "title": info.get("title", "Unknown"),
        "artist": info.get("uploader", "Unknown"),
        "duration": info.get("duration"),
        "thumbnail": info.get("thumbnail"),
        "url": url,
        "video_id": info.get("id", ""),
        "platform": "soundcloud",
    }
