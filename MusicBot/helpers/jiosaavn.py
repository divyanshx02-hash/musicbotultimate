from typing import Optional

import aiohttp
from loguru import logger

JIOSAAVN_BASE = "https://saavn.dev/api"


async def search_jiosaavn(query: str, limit: int = 5) -> list[dict]:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{JIOSAAVN_BASE}/search/songs",
                params={"query": query, "page": 1, "limit": limit},
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status != 200:
                    return []
                data = await resp.json()
                results = data.get("data", {}).get("results", [])
                tracks = []
                for r in results:
                    dl_urls = r.get("downloadUrl", [])
                    best_url = ""
                    for dl in reversed(dl_urls):  # take highest quality
                        if dl.get("url"):
                            best_url = dl["url"]
                            break
                    artists = ", ".join(a.get("name", "") for a in r.get("artists", {}).get("primary", []))
                    tracks.append({
                        "title": r.get("name", "Unknown"),
                        "artist": artists,
                        "album": r.get("album", {}).get("name", ""),
                        "duration": r.get("duration", 0),
                        "thumbnail": r.get("image", [{}])[-1].get("url", ""),
                        "stream_url": best_url,
                        "platform": "jiosaavn",
                    })
                return tracks
    except Exception as e:
        logger.error(f"JioSaavn search error: {e}")
    return []


async def resolve_jiosaavn_url(url: str) -> Optional[dict]:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{JIOSAAVN_BASE}/songs",
                params={"link": url},
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                songs = data.get("data", [])
                if not songs:
                    return None
                r = songs[0]
                dl_urls = r.get("downloadUrl", [])
                best_url = ""
                for dl in reversed(dl_urls):
                    if dl.get("url"):
                        best_url = dl["url"]
                        break
                artists = ", ".join(a.get("name", "") for a in r.get("artists", {}).get("primary", []))
                return {
                    "title": r.get("name", "Unknown"),
                    "artist": artists,
                    "album": r.get("album", {}).get("name", ""),
                    "duration": r.get("duration", 0),
                    "thumbnail": r.get("image", [{}])[-1].get("url", ""),
                    "stream_url": best_url,
                    "platform": "jiosaavn",
                }
    except Exception as e:
        logger.error(f"JioSaavn URL resolve error: {e}")
    return None
