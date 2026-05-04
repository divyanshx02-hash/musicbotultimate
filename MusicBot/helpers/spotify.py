from typing import Optional

import aiohttp
from loguru import logger

from config import SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET

_token_cache: dict = {}


async def get_spotify_token() -> Optional[str]:
    import time
    if _token_cache.get("token") and _token_cache.get("expires_at", 0) > time.time():
        return _token_cache["token"]

    if not (SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET):
        return None

    try:
        import base64
        creds = base64.b64encode(f"{SPOTIFY_CLIENT_ID}:{SPOTIFY_CLIENT_SECRET}".encode()).decode()
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://accounts.spotify.com/api/token",
                headers={"Authorization": f"Basic {creds}"},
                data={"grant_type": "client_credentials"},
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                data = await resp.json()
                token = data.get("access_token")
                expires_in = data.get("expires_in", 3600)
                if token:
                    _token_cache["token"] = token
                    _token_cache["expires_at"] = time.time() + expires_in - 60
                    return token
    except Exception as e:
        logger.error(f"Spotify token error: {e}")
    return None


async def resolve_spotify_track(url: str) -> Optional[dict]:
    import re
    token = await get_spotify_token()
    if not token:
        return None

    match = re.search(r"track/([a-zA-Z0-9]+)", url)
    if not match:
        return None
    track_id = match.group(1)

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"https://api.spotify.com/v1/tracks/{track_id}",
                headers={"Authorization": f"Bearer {token}"},
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                artists = ", ".join(a["name"] for a in data.get("artists", []))
                return {
                    "title": data.get("name", "Unknown"),
                    "artist": artists,
                    "album": data.get("album", {}).get("name", ""),
                    "thumbnail": (data.get("album", {}).get("images") or [{}])[0].get("url"),
                    "duration": data.get("duration_ms", 0) // 1000,
                    "platform": "spotify",
                    "search_query": f"{data.get('name')} {artists}",
                }
    except Exception as e:
        logger.error(f"Spotify track resolve error: {e}")
    return None


async def resolve_spotify_playlist(url: str) -> list[dict]:
    import re
    token = await get_spotify_token()
    if not token:
        return []

    match = re.search(r"playlist/([a-zA-Z0-9]+)", url)
    if not match:
        return []
    playlist_id = match.group(1)

    tracks = []
    try:
        next_url = f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks?limit=50"
        async with aiohttp.ClientSession() as session:
            while next_url and len(tracks) < 200:
                async with session.get(
                    next_url,
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as resp:
                    if resp.status != 200:
                        break
                    data = await resp.json()
                    for item in data.get("items", []):
                        t = item.get("track")
                        if not t:
                            continue
                        artists = ", ".join(a["name"] for a in t.get("artists", []))
                        tracks.append({
                            "title": t.get("name", "Unknown"),
                            "artist": artists,
                            "thumbnail": (t.get("album", {}).get("images") or [{}])[0].get("url"),
                            "duration": t.get("duration_ms", 0) // 1000,
                            "platform": "spotify",
                            "search_query": f"{t.get('name')} {artists}",
                        })
                    next_url = data.get("next")
    except Exception as e:
        logger.error(f"Spotify playlist error: {e}")
    return tracks


async def resolve_spotify_album(url: str) -> list[dict]:
    import re
    token = await get_spotify_token()
    if not token:
        return []

    match = re.search(r"album/([a-zA-Z0-9]+)", url)
    if not match:
        return []
    album_id = match.group(1)

    tracks = []
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"https://api.spotify.com/v1/albums/{album_id}/tracks?limit=50",
                headers={"Authorization": f"Bearer {token}"},
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status != 200:
                    return []
                data = await resp.json()
                for t in data.get("items", []):
                    artists = ", ".join(a["name"] for a in t.get("artists", []))
                    tracks.append({
                        "title": t.get("name", "Unknown"),
                        "artist": artists,
                        "platform": "spotify",
                        "search_query": f"{t.get('name')} {artists}",
                    })
    except Exception as e:
        logger.error(f"Spotify album error: {e}")
    return tracks


async def resolve_spotify_url(url: str) -> list[dict]:
    if "/track/" in url:
        track = await resolve_spotify_track(url)
        return [track] if track else []
    elif "/playlist/" in url:
        return await resolve_spotify_playlist(url)
    elif "/album/" in url:
        return await resolve_spotify_album(url)
    return []
