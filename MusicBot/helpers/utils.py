import math
import os
import re
from typing import Optional


def format_duration(seconds: int) -> str:
    if not seconds:
        return "0:00"
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def progress_bar(current: int, total: int, length: int = 10) -> str:
    if total <= 0:
        return "░" * length
    filled = int(length * current / total)
    return "▓" * filled + "░" * (length - filled)


def humanize_bytes(size: int) -> str:
    if size < 1024:
        return f"{size} B"
    for unit in ("KB", "MB", "GB"):
        size /= 1024
        if size < 1024:
            return f"{size:.1f} {unit}"
    return f"{size:.1f} TB"


def sanitize_html(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def extract_args(text: str) -> str:
    parts = text.strip().split(None, 1)
    return parts[1] if len(parts) > 1 else ""


def split_pages(items: list, page_size: int = 5) -> list[list]:
    return [items[i:i + page_size] for i in range(0, len(items), page_size)]


def clean_file(path: str):
    try:
        if path and os.path.exists(path):
            os.remove(path)
    except Exception:
        pass


def is_youtube_url(url: str) -> bool:
    return bool(re.match(r"https?://(www\.)?(youtube\.com|youtu\.be)/", url))


def is_valid_url(url: str) -> bool:
    return bool(re.match(r"https?://", url.strip()))


def get_readable_time(seconds: int) -> str:
    periods = [("day", 86400), ("hour", 3600), ("minute", 60), ("second", 1)]
    parts = []
    for name, dur in periods:
        value, seconds = divmod(seconds, dur)
        if value:
            parts.append(f"{value} {name}{'s' if value > 1 else ''}")
    return ", ".join(parts) or "0 seconds"


def truncate(text: str, max_len: int = 50, suffix: str = "...") -> str:
    if len(text) <= max_len:
        return text
    return text[:max_len - len(suffix)] + suffix


async def get_user_mention(user) -> str:
    if user.username:
        return f"@{user.username}"
    name = user.first_name or "User"
    return f'<a href="tg://user?id={user.id}">{sanitize_html(name)}</a>'


def parse_time_arg(text: str) -> Optional[int]:
    text = text.strip().lower()
    if text.isdigit():
        return int(text)
    match = re.match(r"(\d+)([smhd])", text)
    if not match:
        return None
    val = int(match.group(1))
    unit = match.group(2)
    return val * {"s": 1, "m": 60, "h": 3600, "d": 86400}[unit]
