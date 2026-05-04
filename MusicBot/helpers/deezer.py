import re
from typing import Optional

import aiohttp
from loguru import logger

from config import DEEZER_ARL


async def resolve_deezer_track(url: str) -> Optional[dict]:
    match = re.search(r"track/(\d+)", url)
    if not match:
        return None
    track_id = match.group(1)
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"https://api.deezer.com/track/{track_id}",
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                artist = data.get("artist", {}).get("name", "Unknown")
                album = data.get("album", {})
                return {
                    "title": data.get("title", "Unknown"),
                    "artist": artist,
                    "album": album.get("title", ""),
                    "thumbnail": album.get("cover_xl") or album.get("cover_big") or "",
                    "duration": data.get("duration", 0),
                    "platform": "deezer",
                    "search_query": f"{data.get('title')} {artist}",
                }
    except Exception as e:
        logger.error(f"Deezer track error: {e}")
    return None


async def resolve_deezer_playlist(url: str) -> list[dict]:
    match = re.search(r"playlist/(\d+)", url)
    if not match:
        return []
    playlist_id = match.group(1)
    tracks = []
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"https://api.deezer.com/playlist/{playlist_id}/tracks?limit=100",
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                if resp.status != 200:
                    return []
                data = await resp.json()
                for t in data.get("data", []):
                    artist = t.get("artist", {}).get("name", "Unknown")
                    tracks.append({
                        "title": t.get("title", "Unknown"),
                        "artist": artist,
                        "platform": "deezer",
                        "search_query": f"{t.get('title')} {artist}",
                    })
    except Exception as e:
        logger.error(f"Deezer playlist error: {e}")
    return tracks


async def resolve_deezer_url(url: str) -> list[dict]:
    if "/track/" in url:
        track = await resolve_deezer_track(url)
        return [track] if track else []
    elif "/playlist/" in url:
        return await resolve_deezer_playlist(url)
    return []
