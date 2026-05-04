from typing import Optional

import aiohttp
from loguru import logger

from config import GENIUS_ACCESS_TOKEN


async def get_lyrics_genius(song: str, artist: str = "") -> Optional[dict]:
    if not GENIUS_ACCESS_TOKEN:
        return None
    try:
        query = f"{song} {artist}".strip()
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://api.genius.com/search",
                headers={"Authorization": f"Bearer {GENIUS_ACCESS_TOKEN}"},
                params={"q": query},
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                hits = data.get("response", {}).get("hits", [])
                if not hits:
                    return None
                hit = hits[0]["result"]
                lyrics_url = hit.get("url", "")
                title = hit.get("title", song)
                artist_name = hit.get("primary_artist", {}).get("name", artist)
                thumbnail = hit.get("song_art_image_url", "")

                lyrics = await _scrape_genius_lyrics(lyrics_url)
                if not lyrics:
                    return None

                return {
                    "title": title,
                    "artist": artist_name,
                    "lyrics": lyrics,
                    "thumbnail": thumbnail,
                    "source": "Genius",
                }
    except Exception as e:
        logger.error(f"Genius lyrics error: {e}")
    return None


async def _scrape_genius_lyrics(url: str) -> Optional[str]:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                if resp.status != 200:
                    return None
                html = await resp.text()
                import re
                # Extract lyrics text from Genius HTML
                pattern = re.compile(r'<div[^>]*data-lyrics-container[^>]*>(.*?)</div>', re.DOTALL)
                matches = pattern.findall(html)
                if not matches:
                    return None
                raw = " ".join(matches)
                # Strip HTML tags
                clean = re.sub(r"<br\s*/?>", "\n", raw)
                clean = re.sub(r"<[^>]+>", "", clean)
                clean = clean.replace("&#x27;", "'").replace("&amp;", "&").replace("&quot;", '"')
                clean = "\n".join(line.strip() for line in clean.splitlines())
                clean = re.sub(r"\n{3,}", "\n\n", clean).strip()
                return clean if len(clean) > 50 else None
    except Exception as e:
        logger.error(f"Genius scrape error: {e}")
    return None


async def get_lyrics_azlyrics(song: str, artist: str = "") -> Optional[dict]:
    try:
        import re
        # Build AZLyrics URL
        clean_artist = re.sub(r"[^a-z0-9]", "", artist.lower().replace("the ", ""))
        clean_song = re.sub(r"[^a-z0-9]", "", song.lower())
        url = f"https://www.azlyrics.com/lyrics/{clean_artist}/{clean_song}.html"

        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                if resp.status != 200:
                    return None
                html = await resp.text()
                # AZLyrics lyrics are in a comment-delimited div
                match = re.search(
                    r"<!-- Usage of azlyrics\.com.*?-->(.*?)<!-- MxM banner -->",
                    html,
                    re.DOTALL,
                )
                if not match:
                    return None
                raw = match.group(1)
                clean = re.sub(r"<[^>]+>", "", raw).strip()
                clean = re.sub(r"\n{3,}", "\n\n", clean)
                return {
                    "title": song,
                    "artist": artist,
                    "lyrics": clean,
                    "source": "AZLyrics",
                }
    except Exception as e:
        logger.error(f"AZLyrics error: {e}")
    return None


async def get_lyrics(song: str, artist: str = "") -> Optional[dict]:
    result = await get_lyrics_genius(song, artist)
    if result:
        return result
    result = await get_lyrics_azlyrics(song, artist)
    return result


def paginate_lyrics(lyrics: str, page_size: int = 3000) -> list[str]:
    pages = []
    lines = lyrics.split("\n")
    current = []
    length = 0
    for line in lines:
        if length + len(line) + 1 > page_size:
            pages.append("\n".join(current))
            current = [line]
            length = len(line)
        else:
            current.append(line)
            length += len(line) + 1
    if current:
        pages.append("\n".join(current))
    return pages or ["No lyrics found."]
