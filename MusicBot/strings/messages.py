from strings.emojis import *

# ── Start & Help ──────────────────────────────────────────────────────────────

START_TEXT = (
    f"<b>{MUSIC} MusicBot — Advanced Free Music Bot</b>\n\n"
    f"Stream music and videos in your group voice chats.\n"
    f"Every feature is free. No limits. No paywalls.\n\n"
    f"<b>Quick Start:</b>\n"
    f"• <code>/play [song name or URL]</code> — Play audio\n"
    f"• <code>/vplay [URL]</code> — Play video\n"
    f"• <code>/help</code> — Full command list\n\n"
    f"Add me to your group and make me admin, then hit play!"
)

HELP_MUSIC = (
    f"<b>{MUSIC} Music Commands</b>\n\n"
    f"/play [song/URL] — Play audio in VC\n"
    f"/vplay [URL] — Play video in VC\n"
    f"/pause — Pause playback\n"
    f"/resume — Resume playback\n"
    f"/skip — Skip current song\n"
    f"/stop — Stop and clear queue\n"
    f"/replay — Replay current song\n"
    f"/seek [seconds] — Seek to position\n"
    f"/queue — View the queue\n"
    f"/shuffle — Shuffle queue\n"
    f"/clearqueue — Clear queue (admin)\n"
    f"/loop [off/one/all] — Set loop mode\n"
    f"/volume [0-200] — Set volume\n"
    f"/effect — Select audio effect\n"
    f"/lyrics [song] — Get lyrics\n"
    f"/fav — Save current song\n"
    f"/favlist — Your saved songs\n"
    f"/identify — Identify a song\n"
    f"/radio — List radio stations\n"
    f"/live [URL] — Stream YouTube live\n"
    f"/download — Download current song\n"
)

HELP_ADMIN = (
    f"<b>{ADMIN} Admin Commands</b>\n\n"
    f"/ban [user] — Ban from bot\n"
    f"/unban [user] — Unban user\n"
    f"/kick [user] — Kick from group\n"
    f"/mute [user] — Mute user\n"
    f"/unmute [user] — Unmute user\n"
    f"/warn [user] [reason] — Warn user\n"
    f"/warns [user] — View warnings\n"
    f"/resetwarn [user] — Reset warnings\n"
    f"/purge [count] — Delete messages\n"
    f"/pin — Pin replied message\n"
    f"/unpin — Unpin message\n"
    f"/setwelcome [text] — Set welcome msg\n"
    f"/setrules [text] — Set group rules\n"
    f"/rules — Show group rules\n"
    f"/antilink [on/off] — Auto-delete links\n"
    f"/antispam [on/off] — Anti-flood\n"
    f"/openqueue [on/off] — Allow all to add\n"
    f"/setvoteskip [N] — Skip threshold\n"
    f"/settimezone [tz] — Set timezone\n"
    f"/setlang [code] — Set language\n"
    f"/enable247 — Keep bot in VC 24/7\n"
)

HELP_GAMES = (
    f"<b>{QUIZ} Game & Fun Commands</b>\n\n"
    f"/musicquiz [rounds] [genre] — Start quiz\n"
    f"/stopquiz — Stop ongoing quiz\n"
    f"/quizleaderboard — Group champions\n"
    f"/globalquiz — All-time top players\n"
    f"/voteskip — Vote to skip current song\n"
    f"/top10 — Most liked songs in this group\n"
    f"/flop10 — Most disliked songs\n"
    f"/recommend — AI song recommendations\n"
    f"/mood [keyword] — AI mood playlist\n"
    f"/wrapped [year] — Your music year recap\n"
    f"/groupwrapped — Group stats card\n"
)

HELP_INFO = (
    f"<b>{INFO} Info & Settings</b>\n\n"
    f"/ping — Check bot latency\n"
    f"/uptime — Bot uptime\n"
    f"/stats — Usage statistics\n"
    f"/sleep [minutes] — Stop music timer\n"
    f"/schedule [time] [song] — Auto-play\n"
    f"/alarm [HH:MM] [message] — Set alarm\n"
    f"/viewschedule — View schedules\n"
    f"/cancelschedule — Cancel schedules\n"
    f"/upcoming [artist] — Upcoming concerts\n"
)

# ── Playback ──────────────────────────────────────────────────────────────────

SEARCHING = f"{SEARCH} <b>Searching for:</b> <code>{{query}}</code>"
DOWNLOADING = f"{LOADING} <b>Downloading:</b> <code>{{title}}</code>"
STREAMING = f"{PLAY} <b>Now streaming...</b>"
ADDED_TO_QUEUE = f"{QUEUE} <b>Added to queue:</b> <code>{{title}}</code> — Position: <b>{{pos}}</b>"

NOW_PLAYING = (
    f"{PLAY} <b>Now Playing</b>\n\n"
    f"<b>{{title}}</b>\n"
    f"<i>{{artist}}</i>\n\n"
    f"{MUSIC} <b>Platform:</b> {{platform}}\n"
    f"<b>Duration:</b> {{duration}}\n"
    f"<b>Requested by:</b> {{requester}}\n"
    f"<b>Queue:</b> {{queue_pos}}\n"
    f"<b>Effect:</b> {{effect}}\n"
    f"<b>Loop:</b> {{loop}}\n"
    f"<b>Volume:</b> {{volume}}%\n\n"
    f"<code>{{progress_bar}}</code>"
)

PAUSED = f"{PAUSE} <b>Playback paused.</b>"
RESUMED = f"{PLAY} <b>Playback resumed.</b>"
SKIPPED = f"{SKIP} <b>Skipped.</b> Playing next song..."
STOPPED = f"{STOP} <b>Playback stopped.</b> Queue cleared."
REPLAYED = f"{PLAY} <b>Replaying current song.</b>"
QUEUE_EMPTY = f"{WARN} <b>The queue is empty.</b> Use /play to add songs."
NO_ACTIVE_STREAM = f"{ERROR} <b>No active stream.</b> Use /play to start."
VOLUME_SET = f"{VOL_UP} <b>Volume set to</b> {{volume}}%"
LOOP_SET = f"{LOOP} <b>Loop mode set to:</b> <b>{{mode}}</b>"

# ── Queue ─────────────────────────────────────────────────────────────────────

QUEUE_HEADER = f"{QUEUE} <b>Queue</b> — {{count}} song(s)"
QUEUE_ITEM = "{pos}. <b>{title}</b> — <i>{artist}</i> [{duration}] by {requester}"
REMOVED_FROM_QUEUE = f"{CHECK} <b>Removed from queue:</b> <code>{{title}}</code>"
QUEUE_SHUFFLED = f"{SHUFFLE} <b>Queue shuffled.</b>"
QUEUE_CLEARED = f"{CHECK} <b>Queue cleared.</b>"
DUPLICATE_IN_QUEUE = f"{WARN} <b>{{title}}</b> is already in the queue."

# ── Effects ───────────────────────────────────────────────────────────────────

EFFECT_SET = f"{EFFECTS} <b>Audio effect changed to:</b> <b>{{effect}}</b>"
SELECT_EFFECT = f"{EFFECTS} <b>Select an audio effect:</b>"

# ── Lyrics ────────────────────────────────────────────────────────────────────

LYRICS_HEADER = f"{LYRICS} <b>{{title}}</b> — <i>{{artist}}</i>\n<i>Source: {{source}}</i>\n\n"
LYRICS_NOT_FOUND = f"{ERROR} <b>Lyrics not found for:</b> <code>{{query}}</code>"

# ── Recognition ──────────────────────────────────────────────────────────────

IDENTIFYING = f"{SEARCH} <b>Identifying your song...</b>"
IDENTIFIED = (
    f"{CHECK} <b>Song Identified!</b>\n\n"
    f"<b>Title:</b> {{title}}\n"
    f"<b>Artist:</b> {{artist}}\n"
    f"<b>Album:</b> {{album}}\n"
    f"<b>Released:</b> {{release_date}}\n"
    f"<b>Confidence:</b> {{score}}%\n"
    f"<i>Source: {{source}}</i>"
)
IDENTIFY_FAILED = f"{ERROR} <b>Could not identify this song.</b> Try a clearer audio sample."

# ── Favourites ────────────────────────────────────────────────────────────────

ADDED_FAV = f"{HEART} <b>Added to your favourites:</b> <code>{{title}}</code>"
REMOVED_FAV = f"{HEART} <b>Removed from favourites:</b> <code>{{title}}</code>"
FAV_LIST_EMPTY = f"{HEART} <b>Your favourites list is empty.</b> Like songs with the ❤️ button!"

# ── Admin / Management ────────────────────────────────────────────────────────

BANNED = f"{BAN} <b>{{user}}</b> has been banned."
UNBANNED = f"{CHECK} <b>{{user}}</b> has been unbanned."
KICKED = f"{BAN} <b>{{user}}</b> has been kicked."
MUTED = f"{MUTE} <b>{{user}}</b> has been muted."
UNMUTED = f"{CHECK} <b>{{user}}</b> has been unmuted."
WARNED = f"{WARN} <b>{{user}}</b> warned. (<b>{{count}}/3</b>)\nReason: <code>{{reason}}</code>"
AUTO_KICKED = f"{BAN} <b>{{user}}</b> was auto-kicked after 3 warnings."
RULES_SET = f"{CHECK} <b>Group rules updated.</b>"
WELCOME_SET = f"{CHECK} <b>Welcome message updated.</b>"

# ── Owner commands ────────────────────────────────────────────────────────────

BROADCAST_DONE = f"{CHECK} <b>Broadcast sent to {{count}} chats.</b>"
MAINTENANCE_ON = f"{SETTINGS} <b>Maintenance mode enabled.</b> Bot is now offline for non-owners."
MAINTENANCE_OFF = f"{SETTINGS} <b>Maintenance mode disabled.</b> Bot is back online."
BOT_STATS = (
    f"{STATS} <b>Bot Statistics</b>\n\n"
    f"<b>Users:</b> {{users}}\n"
    f"<b>Groups:</b> {{chats}}\n"
    f"<b>Songs Played:</b> {{songs_played}}\n"
    f"<b>Sudo Users:</b> {{sudo_users}}\n"
    f"<b>Uptime:</b> {{uptime}}\n"
    f"<b>Assistants:</b> {{assistants}}"
)

# ── Quiz ──────────────────────────────────────────────────────────────────────

QUIZ_START = f"{QUIZ} <b>Music Quiz started!</b> Rounds: <b>{{rounds}}</b> | Genre: <b>{{genre}}</b>"
QUIZ_ROUND = f"{MUSIC} <b>Round {{current}}/{{total}}</b> — Name this song! You have <b>30 seconds...</b>"
QUIZ_CORRECT = f"{PARTY} <b>{{user}}</b> got it right! The song was: <b>{{title}}</b>"
QUIZ_TIMEOUT = f"{CLOCK} <b>Time's up!</b> The song was: <b>{{title}}</b> by <i>{{artist}}</i>"
QUIZ_END = f"{TROPHY} <b>Quiz ended!</b>\n\n{{leaderboard}}"
QUIZ_ALREADY = f"{WARN} <b>A quiz is already running in this group.</b>"
QUIZ_NONE = f"{ERROR} <b>No quiz is running.</b>"

# ── Scheduler ─────────────────────────────────────────────────────────────────

SLEEP_SET = f"{CLOCK} <b>Music will stop in {{minutes}} minutes.</b>"
SCHEDULE_SET = f"{CALENDAR} <b>Scheduled:</b> <code>{{query}}</code> at <b>{{time}}</b>"
ALARM_SET = f"{CLOCK} <b>Alarm set for {{time}}.</b>"

# ── Vote skip ─────────────────────────────────────────────────────────────────

VOTE_SKIP_POLL = f"{VOTE} <b>Vote to skip current song</b>\nNeed <b>{{needed}}</b> votes to skip."
VOTE_SKIP_DONE = f"{SKIP} <b>Vote skip passed!</b> Skipping..."
VOTE_SKIP_ALREADY = f"{WARN} <b>You already voted.</b>"

# ── AI ────────────────────────────────────────────────────────────────────────

RECOMMEND_HEADER = f"{AI} <b>AI Music Recommendations for you:</b>"
MOOD_HEADER = f"{MOOD} <b>{{mood}} Playlist — 10 Songs Queued</b>"
RECOMMEND_LOADING = f"{LOADING} <b>Analyzing your listening history...</b>"

# ── Wrapped ───────────────────────────────────────────────────────────────────

WRAPPED_LOADING = f"{WRAPPED} <b>Generating your music recap...</b>"
WRAPPED_EMPTY = f"{WARN} <b>No listening history found for {{year}}.</b>"

# ── Radio ─────────────────────────────────────────────────────────────────────

RADIO_LIST_HEADER = f"{RADIO} <b>Available Radio Stations:</b>"
RADIO_PLAYING = f"{RADIO} <b>Streaming:</b> <b>{{name}}</b>"

# ── Errors ────────────────────────────────────────────────────────────────────

ERROR_DOWNLOAD = f"{ERROR} <b>Could not download this track.</b> Try a different source."
ERROR_NO_RESULTS = f"{ERROR} <b>No results found for:</b> <code>{{query}}</code>"
ERROR_NOT_IN_VC = f"{ERROR} <b>Bot is not in a voice chat.</b> Start with /play first."
ERROR_JOIN_VC = f"{ERROR} <b>Could not join voice chat.</b> Make sure the bot has the right permissions."
ERROR_GENERIC = f"{ERROR} <b>Something went wrong:</b> <code>{{error}}</code>"
ERROR_PRIVATE_MODE = f"{BAN} <b>This bot is in private mode.</b> Contact the owner for access."
NO_REPLY = f"{WARN} <b>Please reply to a message or provide a username.</b>"
USER_NOT_FOUND = f"{ERROR} <b>User not found.</b>"
