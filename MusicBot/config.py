import os
from dotenv import load_dotenv

load_dotenv()


def _int_list(val: str) -> list[int]:
    return [int(x.strip()) for x in val.split() if x.strip().isdigit()]


# Core credentials
BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
API_ID: int = int(os.getenv("API_ID", "0"))
API_HASH: str = os.getenv("API_HASH", "")
OWNER_ID: list[int] = _int_list(os.getenv("OWNER_ID", ""))
LOGGER_ID: int = int(os.getenv("LOGGER_ID", "0"))

# Assistant sessions
STRING_SESSION: str = os.getenv("STRING_SESSION", "")
STRING_SESSION2: str = os.getenv("STRING_SESSION2", "")
STRING_SESSION3: str = os.getenv("STRING_SESSION3", "")

# Database
MONGO_DB_URI: str = os.getenv("MONGO_DB_URI", "")
REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")

# Cookies
COOKIE_URL: str = os.getenv("COOKIE_URL", "")
COOKIES_FILE: str = "cookies.txt"

# Optional platform APIs
SPOTIFY_CLIENT_ID: str = os.getenv("SPOTIFY_CLIENT_ID", "")
SPOTIFY_CLIENT_SECRET: str = os.getenv("SPOTIFY_CLIENT_SECRET", "")
GENIUS_ACCESS_TOKEN: str = os.getenv("GENIUS_ACCESS_TOKEN", "")
DEEZER_ARL: str = os.getenv("DEEZER_ARL", "")
JIOSAAVN_COOKIE: str = os.getenv("JIOSAAVN_COOKIE", "")
ACRCLOUD_ACCESS_KEY: str = os.getenv("ACRCLOUD_ACCESS_KEY", "")
ACRCLOUD_ACCESS_SECRET: str = os.getenv("ACRCLOUD_ACCESS_SECRET", "")
ACRCLOUD_HOST: str = os.getenv("ACRCLOUD_HOST", "")
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
TICKETMASTER_API_KEY: str = os.getenv("TICKETMASTER_API_KEY", "")

# Fallback download APIs
API_URL: str = os.getenv("API_URL", "")
VIDEO_API_URL: str = os.getenv("VIDEO_API_URL", "")

# File size limits
TG_AUDIO_FILESIZE_LIMIT: int = int(os.getenv("TG_AUDIO_FILESIZE_LIMIT", str(100 * 1024 * 1024)))
TG_VIDEO_FILESIZE_LIMIT: int = int(os.getenv("TG_VIDEO_FILESIZE_LIMIT", str(1024 * 1024 * 1024)))

# Behavior flags
PRIVATE_BOT_MODE: bool = os.getenv("PRIVATE_BOT_MODE", "False").lower() == "true"
AUTO_LEAVING_ASSISTANT: bool = os.getenv("AUTO_LEAVING_ASSISTANT", "True").lower() == "true"
ASSISTANT_LEAVE_TIME: int = int(os.getenv("ASSISTANT_LEAVE_TIME", "300"))
YOUTUBE_EDIT_SLEEP: float = float(os.getenv("YOUTUBE_EDIT_SLEEP", "3"))
TELEGRAM_EDIT_SLEEP: float = float(os.getenv("TELEGRAM_EDIT_SLEEP", "5"))

# Mini App
WEBAPP_URL: str = os.getenv("WEBAPP_URL", "")

# Internal constants
COMMAND_PREFIX: list[str] = ["/"]
MAX_QUEUE_SIZE: int = 500
DEFAULT_VOTE_SKIP_THRESHOLD: int = 3
AUDIO_QUALITY: str = "bestaudio[ext=m4a]/bestaudio/best"
VIDEO_QUALITY: str = "bestvideo[height<=720]+bestaudio/best[height<=720]"
DOWNLOAD_DIR: str = "downloads"
CACHE_TTL: int = 86400
HISTORY_LIMIT: int = 100
QUIZ_CLIP_DURATION: int = 15
QUIZ_ANSWER_TIME: int = 30
COOKIE_REFRESH_INTERVAL: int = 21600  # 6 hours

os.makedirs(DOWNLOAD_DIR, exist_ok=True)
