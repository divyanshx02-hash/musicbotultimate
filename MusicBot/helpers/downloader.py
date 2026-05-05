import asyncio
import os
import re
import subprocess
from typing import Optional

import aiohttp
from loguru import logger

from config import (
    API_URL,
    AUDIO_QUALITY,
    COOKIE_URL,
    COOKIES_FILE,
    DOWNLOAD_DIR,
    VIDEO_QUALITY,
    VIDEO_API_URL,
)

_URL_PATTERN = re.compile(
    r"https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+"
)


def is_valid_url(text: str) -> bool:
    return bool(_URL_PATTERN.match(text.strip()))


async def refresh_cookies():
    if not COOKIE_URL:
        return
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(COOKIE_URL, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status == 200:
                    content = await resp.text()
                    with open(COOKIES_FILE, "w", encoding="utf-8") as f:
                        f.write(content)
                    logger.info(f"Cookies refreshed ({len(content)} bytes)")
    except Exception as e:
        logger.error(f"Failed to refresh cookies: {e}")


def _base_ydl_opts(extra: list[str] = None) -> list[str]:
    opts = ["yt-dlp", "--no-warnings", "--quiet", "--no-playlist"]
    if os.path.exists(COOKIES_FILE):
        opts += ["--cookies", COOKIES_FILE]
    if extra:
        opts += extra
    return opts


async def get_info(url: str) -> Optional[dict]:
    opts = _base_ydl_opts(["--dump-json", "--skip-download", url])
    try:
        proc = await asyncio.create_subprocess_exec(
            *opts,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
        if proc.returncode == 0 and stdout:
            import json
            return json.loads(stdout.decode())
    except asyncio.TimeoutError:
        logger.warning(f"yt-dlp info timeout for {url}")
    except Exception as e:
        logger.error(f"yt-dlp info error: {e}")
    return None


async def search_youtube(query: str, limit: int = 5) -> list[dict]:
    opts = _base_ydl_opts([
        "--dump-json", "--skip-download", "--flat-playlist",
        f"ytsearch{limit}:{query}",
    ])
    results = []
    try:
        proc = await asyncio.create_subprocess_exec(
            *opts,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=30)
        import json
        for line in stdout.decode().splitlines():
            line = line.strip()
            if line:
                try:
                    results.append(json.loads(line))
                except Exception:
                    pass
    except Exception as e:
        logger.error(f"YouTube search error: {e}")
    return results


async def get_audio_stream_url(url: str) -> Optional[str]:
    opts = _base_ydl_opts([
        "--format", AUDIO_QUALITY,
        "--get-url", url,
    ])
    try:
        proc = await asyncio.create_subprocess_exec(
            *opts,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=30)
        if proc.returncode == 0:
            stream_url = stdout.decode().strip()
            if stream_url:
                return stream_url
    except Exception as e:
        logger.error(f"Audio URL fetch error: {e}")

    # Fallback to API
    return await _api_fallback_audio(url)


async def get_video_stream_url(url: str) -> Optional[str]:
    opts = _base_ydl_opts([
        "--format", VIDEO_QUALITY,
        "--get-url", url,
    ])
    try:
        proc = await asyncio.create_subprocess_exec(
            *opts,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=30)
        if proc.returncode == 0:
            lines = stdout.decode().strip().splitlines()
            if lines:
                return lines[0]  # video url (first line)
    except Exception as e:
        logger.error(f"Video URL fetch error: {e}")

    return await _api_fallback_video(url)


async def _api_fallback_audio(url: str) -> Optional[str]:
    if not API_URL:
        return None
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                API_URL,
                params={"url": url, "type": "audio"},
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("url") or data.get("audio_url")
    except Exception as e:
        logger.error(f"API fallback audio error: {e}")
    return None


async def _api_fallback_video(url: str) -> Optional[str]:
    if not VIDEO_API_URL:
        return None
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                VIDEO_API_URL,
                params={"url": url, "type": "video"},
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("url") or data.get("video_url")
    except Exception as e:
        logger.error(f"API fallback video error: {e}")
    return None


def build_ffmpeg_audio_args(stream_url: str, effect_filter: str = "") -> list[str]:
    args = ["ffmpeg", "-hide_banner", "-loglevel", "error"]
    if os.path.exists(COOKIES_FILE):
        args += []
    args += ["-i", stream_url]
    if effect_filter:
        args += ["-af", effect_filter]
    args += [
        "-f", "s16le",
        "-ar", "48000",
        "-ac", "2",
        "pipe:1",
    ]
    return args


def build_ffmpeg_video_args(stream_url: str, audio_url: str = "") -> list[str]:
    args = ["ffmpeg", "-hide_banner", "-loglevel", "error"]
    args += ["-i", stream_url]
    if audio_url and audio_url != stream_url:
        args += ["-i", audio_url]
        args += ["-map", "0:v:0", "-map", "1:a:0"]
    args += [
        "-vf", "scale=1280:720,fps=24",
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-tune", "zerolatency",
        "-c:a", "aac",
        "-b:a", "128k",
        "-f", "mpegts",
        "pipe:1",
    ]
    return args


async def download_clip(url: str, duration: int = 15, output_path: str = None) -> Optional[str]:
    if not output_path:
        output_path = os.path.join(DOWNLOAD_DIR, f"clip_{os.urandom(4).hex()}.mp3")

    stream_url = await get_audio_stream_url(url)
    if not stream_url:
        return None

    args = [
        "ffmpeg", "-hide_banner", "-loglevel", "error",
        "-i", stream_url,
        "-t", str(duration),
        "-q:a", "0",
        "-map", "a",
        output_path,
        "-y",
    ]
    try:
        proc = await asyncio.create_subprocess_exec(
            *args,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await asyncio.wait_for(proc.communicate(), timeout=60)
        if proc.returncode == 0 and os.path.exists(output_path):
            return output_path
        logger.error(f"ffmpeg clip error: {stderr.decode()}")
    except Exception as e:
        logger.error(f"Download clip error: {e}")
    return None


def is_url(text: str) -> bool:
    return bool(re.match(r"https?://", text.strip()))


def detect_platform(url: str) -> str:
    url = url.lower()
    if "youtube.com" in url or "youtu.be" in url:
        return "youtube"
    if "spotify.com" in url:
        return "spotify"
    if "soundcloud.com" in url:
        return "soundcloud"
    if "deezer.com" in url:
        return "deezer"
    if "jiosaavn.com" in url:
        return "jiosaavn"
    if "music.apple.com" in url:
        return "apple"
    if "resso.me" in url:
        return "resso"
    if "tidal.com" in url:
        return "tidal"
    return "unknown"


async def resolve_to_youtube(query: str) -> Optional[dict]:
    results = await search_youtube(query, limit=1)
    if results:
        r = results[0]
        return {
            "title": r.get("title", "Unknown"),
            "url": f"https://www.youtube.com/watch?v={r.get('id', '')}",
            "video_id": r.get("id", ""),
            "duration": r.get("duration"),
            "thumbnail": r.get("thumbnail"),
            "artist": r.get("uploader", ""),
            "platform": "youtube",
        }
    return None
