import json
from typing import Optional

import aiohttp
from loguru import logger

from config import ANTHROPIC_API_KEY, OPENAI_API_KEY


async def get_ai_recommendations(history: list[dict]) -> Optional[list[dict]]:
    if not history:
        return None

    song_list = [f"{t.get('title', 'Unknown')} by {t.get('artist', 'Unknown')}" for t in history[:20]]
    songs_text = ", ".join(song_list)

    prompt = (
        f"Based on these songs the user loves: {songs_text}. "
        "Suggest 5 songs they would enjoy. "
        "Return only a JSON array with objects: [{\"title\": \"...\", \"artist\": \"...\", \"reason\": \"...\"}]"
    )

    result = await _call_anthropic(prompt) or await _call_openai(prompt)
    if result:
        return result

    return _genre_fallback(history)


async def get_mood_playlist(mood: str) -> Optional[list[dict]]:
    prompt = (
        f"Create a 10-song playlist for the mood: {mood}. "
        "Return only a JSON array: [{\"title\": \"...\", \"artist\": \"...\", \"reason\": \"...\"}]"
    )

    result = await _call_anthropic(prompt) or await _call_openai(prompt)
    if result:
        return result[:10]

    return _mood_fallback(mood)


async def _call_anthropic(prompt: str) -> Optional[list[dict]]:
    if not ANTHROPIC_API_KEY:
        return None
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": "claude-haiku-20240307",
                    "max_tokens": 512,
                    "messages": [{"role": "user", "content": prompt}],
                },
                timeout=aiohttp.ClientTimeout(total=20),
            ) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                text = data["content"][0]["text"]
                return _parse_json_list(text)
    except Exception as e:
        logger.error(f"Anthropic API error: {e}")
    return None


async def _call_openai(prompt: str) -> Optional[list[dict]]:
    if not OPENAI_API_KEY:
        return None
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENAI_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "gpt-3.5-turbo",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 512,
                    "temperature": 0.7,
                },
                timeout=aiohttp.ClientTimeout(total=20),
            ) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                text = data["choices"][0]["message"]["content"]
                return _parse_json_list(text)
    except Exception as e:
        logger.error(f"OpenAI API error: {e}")
    return None


def _parse_json_list(text: str) -> Optional[list[dict]]:
    import re
    try:
        match = re.search(r"\[.*\]", text, re.DOTALL)
        if match:
            return json.loads(match.group())
    except Exception:
        pass
    return None


def _genre_fallback(history: list[dict]) -> list[dict]:
    fallback = [
        {"title": "Shape of You", "artist": "Ed Sheeran", "reason": "Popular hit"},
        {"title": "Blinding Lights", "artist": "The Weeknd", "reason": "Chart-topping"},
        {"title": "Stay", "artist": "The Kid LAROI & Justin Bieber", "reason": "Viral hit"},
        {"title": "As It Was", "artist": "Harry Styles", "reason": "Feel-good pop"},
        {"title": "Heat Waves", "artist": "Glass Animals", "reason": "Indie vibes"},
    ]
    return fallback


def _mood_fallback(mood: str) -> list[dict]:
    mood_playlists = {
        "happy": [
            {"title": "Happy", "artist": "Pharrell Williams", "reason": "Pure happiness"},
            {"title": "Can't Stop the Feeling", "artist": "Justin Timberlake", "reason": "Uplifting"},
            {"title": "Good as Hell", "artist": "Lizzo", "reason": "Empowering"},
            {"title": "Walking on Sunshine", "artist": "Katrina and the Waves", "reason": "Classic happy"},
            {"title": "Uptown Funk", "artist": "Bruno Mars", "reason": "Dance-worthy"},
        ],
        "sad": [
            {"title": "Someone Like You", "artist": "Adele", "reason": "Emotional ballad"},
            {"title": "The Night Will Always Win", "artist": "Manchester Orchestra", "reason": "Cathartic"},
            {"title": "Skinny Love", "artist": "Bon Iver", "reason": "Raw emotion"},
            {"title": "Fix You", "artist": "Coldplay", "reason": "Healing"},
            {"title": "Let Her Go", "artist": "Passenger", "reason": "Bittersweet"},
        ],
        "chill": [
            {"title": "Sunset Lover", "artist": "Petit Biscuit", "reason": "Chill vibes"},
            {"title": "Redbone", "artist": "Childish Gambino", "reason": "Smooth groove"},
            {"title": "Electric Feel", "artist": "MGMT", "reason": "Laid-back"},
            {"title": "Best Part", "artist": "Daniel Caesar", "reason": "Mellow R&B"},
            {"title": "Cornelia Street", "artist": "Taylor Swift", "reason": "Soft pop"},
        ],
    }
    result = mood_playlists.get(mood.lower(), [])
    if not result:
        result = mood_playlists["chill"]
    # Pad to 10 if needed
    while len(result) < 10:
        result.extend(result[:10 - len(result)])
    return result[:10]
