import io
import os
import textwrap
from typing import Optional

import aiohttp
from loguru import logger

try:
    from PIL import Image, ImageDraw, ImageFilter, ImageFont
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


FONT_DIR = os.path.join(os.path.dirname(__file__), "..", "assets", "fonts")
DEFAULT_THUMB = os.path.join(os.path.dirname(__file__), "..", "assets", "default_thumb.jpg")


def _get_font(size: int) -> Optional[object]:
    if not PIL_AVAILABLE:
        return None
    paths = [
        os.path.join(FONT_DIR, "NotoSans-Bold.ttf"),
        os.path.join(FONT_DIR, "DejaVuSans-Bold.ttf"),
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ]
    for p in paths:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


async def fetch_thumbnail(url: str) -> Optional[bytes]:
    if not url:
        return None
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    return await resp.read()
    except Exception as e:
        logger.warning(f"Thumbnail fetch failed: {e}")
    return None


async def generate_np_thumbnail(
    title: str,
    artist: str,
    duration: str,
    platform: str,
    requester: str,
    thumb_url: str = None,
) -> Optional[bytes]:
    if not PIL_AVAILABLE:
        return None

    try:
        # Canvas
        img = Image.new("RGB", (1280, 720), color=(15, 15, 20))
        draw = ImageDraw.Draw(img)

        # Background gradient
        for y in range(720):
            r = int(15 + (30 - 15) * y / 720)
            g = int(15 + (25 - 15) * y / 720)
            b = int(20 + (40 - 20) * y / 720)
            draw.line([(0, y), (1280, y)], fill=(r, g, b))

        # Album art
        if thumb_url:
            thumb_data = await fetch_thumbnail(thumb_url)
            if thumb_data:
                thumb_img = Image.open(io.BytesIO(thumb_data)).convert("RGBA")
                thumb_img = thumb_img.resize((380, 380), Image.LANCZOS)
                # Rounded corners effect
                mask = Image.new("L", (380, 380), 0)
                mask_draw = ImageDraw.Draw(mask)
                mask_draw.rounded_rectangle([0, 0, 380, 380], radius=24, fill=255)
                thumb_img.putalpha(mask)
                img.paste(thumb_img, (80, 170), thumb_img)

        # Platform badge
        platform_colors = {
            "youtube": (255, 0, 0),
            "spotify": (30, 215, 96),
            "soundcloud": (255, 85, 0),
            "deezer": (0, 100, 220),
            "apple": (252, 61, 57),
            "jiosaavn": (2, 119, 189),
            "tidal": (0, 212, 255),
            "telegram": (0, 136, 204),
        }
        badge_color = platform_colors.get(platform.lower(), (100, 100, 100))
        draw.rounded_rectangle([500, 130, 700, 168], radius=12, fill=badge_color)
        font_small = _get_font(20)
        draw.text((600, 149), platform.upper(), fill=(255, 255, 255), font=font_small, anchor="mm")

        # Title
        font_title = _get_font(52)
        title_wrapped = textwrap.fill(title[:60], width=28)
        draw.text((500, 200), title_wrapped, fill=(255, 255, 255), font=font_title)

        # Artist
        font_artist = _get_font(34)
        draw.text((500, 330), artist[:40], fill=(180, 180, 190), font=font_artist)

        # Duration & requester
        font_info = _get_font(26)
        draw.text((500, 400), f"Duration: {duration}", fill=(130, 130, 145), font=font_info)
        draw.text((500, 440), f"Requested by: {requester}", fill=(130, 130, 145), font=font_info)

        # Bottom bar
        draw.rounded_rectangle([80, 630, 1200, 660], radius=8, fill=(40, 40, 50))
        draw.rounded_rectangle([80, 630, 400, 660], radius=8, fill=badge_color)

        # Watermark
        font_wm = _get_font(22)
        draw.text((1200, 700), "MusicBot", fill=(60, 60, 70), font=font_wm, anchor="rb")

        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=92)
        buf.seek(0)
        return buf.read()

    except Exception as e:
        logger.error(f"Thumbnail generation error: {e}")
        return None


async def generate_wrapped_card(stats: dict, name: str, year: int) -> Optional[bytes]:
    if not PIL_AVAILABLE:
        return None

    try:
        img = Image.new("RGB", (900, 1200), color=(10, 10, 18))
        draw = ImageDraw.Draw(img)

        # Gradient background
        for y in range(1200):
            r = int(10 + 20 * y / 1200)
            g = int(10 + 10 * y / 1200)
            b = int(18 + 30 * y / 1200)
            draw.line([(0, y), (900, y)], fill=(r, g, b))

        # Accent top strip
        draw.rectangle([0, 0, 900, 8], fill=(0, 200, 120))

        font_xl = _get_font(64)
        font_lg = _get_font(44)
        font_md = _get_font(32)
        font_sm = _get_font(24)

        # Header
        draw.text((450, 80), "Your Year in Music", fill=(255, 255, 255), font=font_xl, anchor="mm")
        draw.text((450, 145), str(year), fill=(0, 200, 120), font=font_lg, anchor="mm")
        draw.text((450, 185), name, fill=(150, 150, 165), font=font_md, anchor="mm")

        # Stats cards
        card_data = [
            ("Top Song", stats.get("top_song", "Unknown"), (0, 180, 120)),
            ("Top Artist", stats.get("top_artist", "Unknown"), (0, 140, 200)),
            ("Songs Played", str(stats.get("total_songs", 0)), (200, 100, 0)),
            ("Listening Streak", f"{stats.get('streak', 0)} days", (180, 0, 80)),
        ]
        y_start = 240
        for label, value, color in card_data:
            draw.rounded_rectangle([60, y_start, 840, y_start + 110], radius=16, fill=(25, 25, 38))
            draw.rounded_rectangle([60, y_start, 16 + 60, y_start + 110], radius=8, fill=color)
            draw.text((120, y_start + 28), label, fill=(150, 150, 165), font=font_sm)
            draw.text((120, y_start + 60), value[:40], fill=(255, 255, 255), font=font_md)
            y_start += 130

        # Peak hour chart
        hour_data = stats.get("hour_data", {})
        if hour_data:
            draw.text((60, y_start + 10), "Peak Listening Hours", fill=(200, 200, 210), font=font_md)
            y_start += 55
            max_val = max(hour_data.values()) if hour_data else 1
            bar_w = int((840 - 60) / 24) - 2
            for h in range(24):
                val = hour_data.get(h, 0)
                bar_h = int(80 * val / max_val) if max_val else 0
                x0 = 60 + h * (bar_w + 2)
                intensity = int(50 + 150 * val / max_val) if max_val else 50
                draw.rectangle(
                    [x0, y_start + 80 - bar_h, x0 + bar_w, y_start + 80],
                    fill=(0, intensity, 120),
                )
            peak_h = stats.get("peak_hour", 0)
            draw.text((60, y_start + 90), f"Peak: {peak_h:02d}:00", fill=(130, 130, 145), font=font_sm)
            y_start += 130

        # Footer
        draw.text((450, 1170), "MusicBot • Free for everyone", fill=(60, 65, 80), font=font_sm, anchor="mm")

        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=90)
        buf.seek(0)
        return buf.read()

    except Exception as e:
        logger.error(f"Wrapped card error: {e}")
        return None
