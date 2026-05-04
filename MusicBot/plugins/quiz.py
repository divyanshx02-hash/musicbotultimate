import asyncio
import random

from loguru import logger
from pyrogram import Client, filters
from pyrogram.types import Message

from helpers.decorators import anti_flood, is_admin
from helpers.downloader import download_clip, search_youtube
from helpers.utils import clean_file, sanitize_html
from strings.messages import QUIZ_ALREADY, QUIZ_CORRECT, QUIZ_END, QUIZ_NONE, QUIZ_ROUND, QUIZ_START, QUIZ_TIMEOUT

GENRE_QUERIES = {
    "pop": "popular pop songs 2023",
    "rock": "best rock songs all time",
    "bollywood": "popular bollywood songs",
    "kpop": "popular kpop songs",
    "rap": "popular rap hip hop songs",
    "jazz": "classic jazz songs",
    "classical": "famous classical music",
    "random": "popular songs playlist",
}

# Active quiz answer watchers per chat
_active_quizzes: dict[int, asyncio.Event] = {}
_quiz_answers: dict[int, tuple] = {}  # chat_id -> (user_id, username, answer_text)


@Client.on_message(filters.command("musicquiz") & (filters.group | filters.channel))
@anti_flood
async def musicquiz_command(client: Client, message: Message):
    from bot import cache

    chat_id = message.chat.id
    state = await cache.get_quiz_state(chat_id)
    if state and state.get("active"):
        await message.reply(QUIZ_ALREADY)
        return

    args = message.command[1:]
    rounds = 5
    genre = "random"
    for arg in args:
        if arg.isdigit():
            rounds = min(max(int(arg), 1), 15)
        elif arg.lower() in GENRE_QUERIES:
            genre = arg.lower()

    await message.reply(QUIZ_START.format(rounds=rounds, genre=genre))
    asyncio.create_task(_run_quiz(client, chat_id, rounds, genre))


@Client.on_message(filters.command("stopquiz") & (filters.group | filters.channel))
@is_admin
async def stopquiz_command(client: Client, message: Message):
    from bot import cache
    state = await cache.get_quiz_state(message.chat.id)
    if not state or not state.get("active"):
        await message.reply(QUIZ_NONE)
        return
    state["stopped"] = True
    await cache.set_quiz_state(message.chat.id, state)
    # Wake up any waiting round
    if message.chat.id in _active_quizzes:
        _active_quizzes[message.chat.id].set()
    await message.reply("<b>Quiz stopped by admin.</b>")


@Client.on_message(filters.command("quizleaderboard") & (filters.group | filters.channel))
async def quiz_leaderboard(client: Client, message: Message):
    from bot import db
    board = await db.get_quiz_leaderboard(message.chat.id)
    if not board:
        await message.reply("<b>No quiz scores yet. Start with /musicquiz!</b>")
        return
    medals = ["🥇", "🥈", "🥉"]
    lines = ["<b>Quiz Leaderboard</b>\n"]
    for i, entry in enumerate(board):
        medal = medals[i] if i < 3 else f"{i+1}."
        username = sanitize_html(entry.get("username", "Unknown"))
        points = entry.get("points", 0)
        lines.append(f"{medal} <b>{username}</b> — {points} pts")
    await message.reply("\n".join(lines))


@Client.on_message(filters.command("globalquiz") & (filters.group | filters.private))
async def global_quiz_leaderboard(client: Client, message: Message):
    from bot import db
    board = await db.get_global_quiz_leaderboard()
    if not board:
        await message.reply("<b>No global quiz scores yet.</b>")
        return
    medals = ["🥇", "🥈", "🥉"]
    lines = ["<b>Global Quiz Leaderboard</b>\n"]
    for i, entry in enumerate(board):
        medal = medals[i] if i < 3 else f"{i+1}."
        username = sanitize_html(entry.get("username", f"User {entry['_id']}"))
        points = entry.get("points", 0)
        lines.append(f"{medal} <b>{username}</b> — {points} pts")
    await message.reply("\n".join(lines))


# Global message handler for quiz answers — always active, filters by chat
@Client.on_message(filters.text & filters.group)
async def _quiz_answer_listener(client: Client, message: Message):
    """Listens for quiz answers in all groups. Only processes active quizzes."""
    chat_id = message.chat.id
    if chat_id not in _active_quizzes:
        return

    from bot import cache
    state = await cache.get_quiz_state(chat_id)
    if not state or not state.get("active") or not state.get("accepting_answers"):
        return

    current_title = state.get("current_title", "")
    if not current_title:
        return

    user = message.from_user
    if not user:
        return

    text = message.text.strip().lower()
    try:
        from fuzzywuzzy import fuzz
        ratio = fuzz.partial_ratio(text, current_title.lower())
    except ImportError:
        ratio = 100 if text in current_title.lower() else 0

    if ratio >= 70:
        _quiz_answers[chat_id] = (user.id, user.first_name or "Someone", message.text)
        _active_quizzes[chat_id].set()  # Signal that an answer was found


async def _run_quiz(client: Client, chat_id: int, rounds: int, genre: str):
    from bot import assistant_manager, cache, db
    from config import QUIZ_ANSWER_TIME, QUIZ_CLIP_DURATION

    scores: dict[int, dict] = {}
    state = {"active": True, "stopped": False, "accepting_answers": False, "current_title": ""}
    await cache.set_quiz_state(chat_id, state)

    for round_num in range(1, rounds + 1):
        state = await cache.get_quiz_state(chat_id)
        if state and state.get("stopped"):
            break

        # Pick a random song
        query = GENRE_QUERIES.get(genre, GENRE_QUERIES["random"])
        results = await search_youtube(f"{query} official", limit=20)
        if not results:
            await client.send_message(chat_id, "<b>Could not find songs. Quiz ended early.</b>")
            break

        song = random.choice(results)
        title = song.get("title", "Unknown")
        video_id = song.get("id", "")
        url = f"https://www.youtube.com/watch?v={video_id}"

        # Download clip
        clip_path = None
        try:
            clip_path = await download_clip(url, duration=QUIZ_CLIP_DURATION)
        except Exception as e:
            logger.error(f"Quiz clip download error: {e}")

        # Play clip in VC or send as audio
        if clip_path and await cache.is_stream_active(chat_id):
            try:
                from helpers.downloader import get_audio_stream_url
                stream_url = await get_audio_stream_url(url)
                if stream_url:
                    await assistant_manager.change_stream(chat_id, stream_url)
            except Exception:
                pass
        elif clip_path:
            try:
                await client.send_audio(chat_id, clip_path, caption=f"🎵 Round {round_num}")
            except Exception:
                pass

        await client.send_message(
            chat_id,
            QUIZ_ROUND.format(current=round_num, total=rounds),
        )

        # Set up answer detection
        event = asyncio.Event()
        _active_quizzes[chat_id] = event
        _quiz_answers.pop(chat_id, None)

        # Enable answer acceptance
        state["accepting_answers"] = True
        state["current_title"] = title
        await cache.set_quiz_state(chat_id, state)

        # Wait for answer or timeout
        try:
            await asyncio.wait_for(event.wait(), timeout=QUIZ_ANSWER_TIME)
        except asyncio.TimeoutError:
            pass

        # Disable answer acceptance
        state["accepting_answers"] = False
        state["current_title"] = ""
        await cache.set_quiz_state(chat_id, state)

        # Check if someone answered correctly
        if chat_id in _quiz_answers:
            user_id, username, _ = _quiz_answers[chat_id]
            scores.setdefault(user_id, {"username": username, "points": 0})
            scores[user_id]["points"] += 1
            await db.add_quiz_point(chat_id, user_id, username)
            await client.send_message(
                chat_id,
                QUIZ_CORRECT.format(user=sanitize_html(username), title=sanitize_html(title)),
            )
        else:
            await client.send_message(
                chat_id,
                QUIZ_TIMEOUT.format(title=sanitize_html(title), artist=""),
            )

        # Cleanup
        _active_quizzes.pop(chat_id, None)
        _quiz_answers.pop(chat_id, None)
        if clip_path:
            clean_file(clip_path)
        await asyncio.sleep(3)

    # Show final leaderboard
    await cache.clear_quiz_state(chat_id)
    _active_quizzes.pop(chat_id, None)
    board = await db.get_quiz_leaderboard(chat_id, limit=10)
    medals = ["🥇", "🥈", "🥉"]
    lb_lines = []
    for i, e in enumerate(board[:5]):
        m = medals[i] if i < 3 else f"{i+1}."
        lb_lines.append(f"{m} <b>{sanitize_html(e.get('username', 'Unknown'))}</b> — {e.get('points', 0)} pts")

    await client.send_message(
        chat_id,
        QUIZ_END.format(leaderboard="\n".join(lb_lines) if lb_lines else "No scores recorded."),
    )
