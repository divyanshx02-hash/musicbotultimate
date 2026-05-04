import base64
import hashlib
import hmac
import os
import time
from typing import Optional

import aiohttp
from loguru import logger

from config import ACRCLOUD_ACCESS_KEY, ACRCLOUD_ACCESS_SECRET, ACRCLOUD_HOST


async def identify_acrcloud(audio_path: str) -> Optional[dict]:
    if not (ACRCLOUD_ACCESS_KEY and ACRCLOUD_ACCESS_SECRET and ACRCLOUD_HOST):
        return None

    try:
        timestamp = str(int(time.time()))
        method = "POST"
        uri = "/v1/identify"
        data_type = "audio"
        signature_version = "1"

        string_to_sign = "\n".join([method, uri, ACRCLOUD_ACCESS_KEY, data_type, signature_version, timestamp])
        sign = base64.b64encode(
            hmac.new(ACRCLOUD_ACCESS_SECRET.encode(), string_to_sign.encode(), hashlib.sha1).digest()
        ).decode()

        with open(audio_path, "rb") as f:
            audio_data = f.read()

        async with aiohttp.ClientSession() as session:
            form = aiohttp.FormData()
            form.add_field("access_key", ACRCLOUD_ACCESS_KEY)
            form.add_field("sample_bytes", str(len(audio_data)))
            form.add_field("timestamp", timestamp)
            form.add_field("signature", sign)
            form.add_field("data_type", data_type)
            form.add_field("signature_version", signature_version)
            form.add_field("sample", audio_data, content_type="application/octet-stream")

            async with session.post(
                f"https://{ACRCLOUD_HOST}/v1/identify",
                data=form,
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                data = await resp.json()

        status = data.get("status", {})
        if status.get("code") != 0:
            return None

        music_list = data.get("metadata", {}).get("music", [])
        if not music_list:
            return None

        m = music_list[0]
        artists = ", ".join(a.get("name", "") for a in m.get("artists", []))
        return {
            "title": m.get("title", "Unknown"),
            "artist": artists or "Unknown",
            "album": m.get("album", {}).get("name", ""),
            "release_date": m.get("release_date", ""),
            "score": m.get("score", 0),
            "source": "ACRCloud",
        }
    except Exception as e:
        logger.error(f"ACRCloud identification error: {e}")
    return None


async def identify_shazamio(audio_path: str) -> Optional[dict]:
    try:
        from shazamio import Shazam
        shazam = Shazam()
        out = await shazam.recognize_song(audio_path)
        matches = out.get("matches", [])
        if not matches:
            return None
        track = out.get("track", {})
        if not track:
            return None
        title = track.get("title", "Unknown")
        artist = track.get("subtitle", "Unknown")
        metadata = {m.get("title", ""): m.get("text", "") for m in track.get("sections", [{}])[0].get("metadata", [])}
        return {
            "title": title,
            "artist": artist,
            "album": metadata.get("Album", ""),
            "release_date": metadata.get("Released", ""),
            "score": 100,
            "source": "Shazam",
        }
    except ImportError:
        logger.warning("shazamio not installed")
    except Exception as e:
        logger.error(f"Shazamio error: {e}")
    return None


async def identify_song(audio_path: str) -> Optional[dict]:
    result = await identify_acrcloud(audio_path)
    if result:
        return result
    return await identify_shazamio(audio_path)
