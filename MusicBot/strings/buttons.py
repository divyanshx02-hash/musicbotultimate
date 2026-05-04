from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

from config import WEBAPP_URL


def now_playing_keyboard(chat_id: int, is_paused: bool = False, loop: str = "off", effect: str = "Normal") -> InlineKeyboardMarkup:
    pause_text = "▶️ Resume" if is_paused else "⏸ Pause"
    loop_icon = {"off": "🔁", "one": "🔂", "all": "🔁✅"}.get(loop, "🔁")
    buttons = [
        [
            InlineKeyboardButton("⏮ Prev", callback_data=f"prev|{chat_id}"),
            InlineKeyboardButton(pause_text, callback_data=f"pause|{chat_id}"),
            InlineKeyboardButton("⏭ Skip", callback_data=f"skip|{chat_id}"),
        ],
        [
            InlineKeyboardButton("🔀 Shuffle", callback_data=f"shuffle|{chat_id}"),
            InlineKeyboardButton(f"{loop_icon} Loop", callback_data=f"loop|{chat_id}"),
            InlineKeyboardButton("⏹ Stop", callback_data=f"stop|{chat_id}"),
        ],
        [
            InlineKeyboardButton("🔉 Vol -10", callback_data=f"vol_down|{chat_id}"),
            InlineKeyboardButton("🔊 Vol +10", callback_data=f"vol_up|{chat_id}"),
            InlineKeyboardButton("📋 Queue", callback_data=f"queue|{chat_id}"),
        ],
        [
            InlineKeyboardButton("🎤 Lyrics", callback_data=f"lyrics|{chat_id}"),
            InlineKeyboardButton("⬇️ Download", callback_data=f"download|{chat_id}"),
            InlineKeyboardButton("❤️ Favourite", callback_data=f"fav|{chat_id}"),
        ],
        [
            InlineKeyboardButton(f"🎛 Effects [{effect}]", callback_data=f"effects_menu|{chat_id}"),
            InlineKeyboardButton("🗳 Vote Skip", callback_data=f"voteskip|{chat_id}"),
        ],
        [
            InlineKeyboardButton("👍 Like", callback_data=f"rate|{chat_id}|1"),
            InlineKeyboardButton("👎 Dislike", callback_data=f"rate|{chat_id}|-1"),
            InlineKeyboardButton("🌐 Source", callback_data=f"source|{chat_id}"),
        ],
    ]
    if WEBAPP_URL:
        buttons.append([
            InlineKeyboardButton("📱 Open Player", web_app=WebAppInfo(url=WEBAPP_URL))
        ])
    return InlineKeyboardMarkup(buttons)


def queue_keyboard(chat_id: int, page: int, total_pages: int) -> InlineKeyboardMarkup:
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("◀️ Prev", callback_data=f"qpage|{chat_id}|{page - 1}"))
    nav.append(InlineKeyboardButton(f"{page + 1}/{total_pages}", callback_data="noop"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton("Next ▶️", callback_data=f"qpage|{chat_id}|{page + 1}"))
    return InlineKeyboardMarkup([nav, [InlineKeyboardButton("« Back", callback_data=f"np_back|{chat_id}")]])


def lyrics_keyboard(page: int, total_pages: int, chat_id: int) -> InlineKeyboardMarkup:
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("◀️", callback_data=f"lpage|{chat_id}|{page - 1}"))
    nav.append(InlineKeyboardButton(f"{page + 1}/{total_pages}", callback_data="noop"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton("▶️", callback_data=f"lpage|{chat_id}|{page + 1}"))
    return InlineKeyboardMarkup([nav])


def identify_result_keyboard(title: str, artist: str, chat_id: int) -> InlineKeyboardMarkup:
    query = f"{title} {artist}"
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("▶️ Play in VC", callback_data=f"id_play|{chat_id}|{query[:60]}"),
            InlineKeyboardButton("🎤 Lyrics", callback_data=f"id_lyrics|{chat_id}|{title[:50]}|{artist[:30]}"),
        ],
        [
            InlineKeyboardButton("🔍 More by Artist", callback_data=f"id_more|{chat_id}|{artist[:40]}"),
        ],
    ])


def recommendation_keyboard(recommendations: list[dict], chat_id: int) -> InlineKeyboardMarkup:
    rows = []
    for i, r in enumerate(recommendations[:5]):
        title = r.get("title", "Unknown")[:40]
        artist = r.get("artist", "")[:20]
        rows.append([InlineKeyboardButton(
            f"▶️ {title} — {artist}",
            callback_data=f"rec_play|{chat_id}|{title}|{artist}",
        )])
    return InlineKeyboardMarkup(rows)


def favlist_keyboard(favs: list[dict], page: int, total_pages: int, user_id: int) -> InlineKeyboardMarkup:
    rows = []
    for f in favs:
        title = f.get("title", "Unknown")[:35]
        vid = f.get("video_id", "")
        rows.append([InlineKeyboardButton(f"▶️ {title}", callback_data=f"fav_play|{user_id}|{vid}")])
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("◀️", callback_data=f"fav_page|{user_id}|{page - 1}"))
    nav.append(InlineKeyboardButton(f"{page + 1}/{total_pages}", callback_data="noop"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton("▶️", callback_data=f"fav_page|{user_id}|{page + 1}"))
    if nav:
        rows.append(nav)
    return InlineKeyboardMarkup(rows) if rows else InlineKeyboardMarkup([[InlineKeyboardButton("Empty", callback_data="noop")]])


def radio_keyboard(stations: list[dict], chat_id: int) -> InlineKeyboardMarkup:
    rows = []
    for s in stations[:20]:
        rows.append([InlineKeyboardButton(
            f"📻 {s.get('name', 'Unknown')} ({s.get('genre', '')})",
            callback_data=f"radio_play|{chat_id}|{s.get('name', '')[:40]}",
        )])
    return InlineKeyboardMarkup(rows)


def help_keyboard(page: int) -> InlineKeyboardMarkup:
    pages = ["🎵 Music", "🛡 Admin", "🎮 Games", "ℹ️ Info"]
    nav = []
    for i, label in enumerate(pages):
        if i == page:
            nav.append(InlineKeyboardButton(f"• {label} •", callback_data="noop"))
        else:
            nav.append(InlineKeyboardButton(label, callback_data=f"help|{i}"))
    rows = [nav]
    return InlineKeyboardMarkup(rows)


def vote_skip_keyboard(chat_id: int, skip_count: int = 0, keep_count: int = 0) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton(f"✅ Skip ({skip_count})", callback_data=f"vs_skip|{chat_id}"),
        InlineKeyboardButton(f"❌ Keep ({keep_count})", callback_data=f"vs_keep|{chat_id}"),
    ]])
