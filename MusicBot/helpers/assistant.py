import asyncio
from typing import Optional

from loguru import logger
from pyrogram import Client
from pytgcalls import PyTgCalls
from pytgcalls.types import AudioPiped, VideoPiped, AudioImagePiped
from pytgcalls.types.input_stream import InputAudioStream, InputVideoStream
from pytgcalls.types.input_stream.quality import (
    HighQualityAudio,
    MediumQualityAudio,
    HighQualityVideo,
    MediumQualityVideo,
)

from config import API_HASH, API_ID, ASSISTANT_LEAVE_TIME, AUTO_LEAVING_ASSISTANT


class AssistantClient:
    def __init__(self, session: str, index: int, api_id: int, api_hash: str):
        self.index = index
        self.client = Client(
            f"assistant_{index}",
            api_id=api_id,
            api_hash=api_hash,
            session_string=session,
        )
        self.call = PyTgCalls(self.client)
        self.available = False
        self.active_chats: set[int] = set()

    async def start(self):
        await self.client.start()
        await self.call.start()
        self.available = True
        me = await self.client.get_me()
        logger.info(f"Assistant {self.index} started: @{me.username}")

    async def stop(self):
        try:
            await self.call.stop()
            await self.client.stop()
        except Exception as e:
            logger.error(f"Error stopping assistant {self.index}: {e}")
        self.available = False

    async def ping(self) -> bool:
        try:
            await self.client.get_me()
            return True
        except Exception:
            return False

    async def join_vc(self, chat_id: int) -> bool:
        try:
            await self.client.join_chat(chat_id)
            return True
        except Exception as e:
            logger.error(f"Assistant {self.index} join_vc error for {chat_id}: {e}")
            return False

    async def leave_vc(self, chat_id: int):
        try:
            await self.call.leave_group_call(chat_id)
            self.active_chats.discard(chat_id)
        except Exception as e:
            logger.error(f"Assistant {self.index} leave_vc error: {e}")

    async def play_audio(self, chat_id: int, stream_url: str, ffmpeg_args: list[str] = None):
        from pytgcalls.types import AudioPiped
        self.active_chats.add(chat_id)
        await self.call.join_group_call(
            chat_id,
            AudioPiped(
                stream_url,
                HighQualityAudio(),
                additional_ffmpeg_parameters=(
                    " ".join(ffmpeg_args) if ffmpeg_args else ""
                ),
            ),
            stream_type=None,
        )

    async def play_video(self, chat_id: int, stream_url: str):
        from pytgcalls.types import VideoPiped
        self.active_chats.add(chat_id)
        await self.call.join_group_call(
            chat_id,
            VideoPiped(
                stream_url,
                HighQualityAudio(),
                HighQualityVideo(),
            ),
        )

    async def change_stream(self, chat_id: int, stream_url: str, ffmpeg_args: list[str] = None):
        await self.call.change_stream(
            chat_id,
            AudioPiped(
                stream_url,
                HighQualityAudio(),
                additional_ffmpeg_parameters=(
                    " ".join(ffmpeg_args) if ffmpeg_args else ""
                ),
            ),
        )

    async def pause(self, chat_id: int):
        try:
            await self.call.pause_stream(chat_id)
        except Exception as e:
            logger.error(f"Pause error for {chat_id}: {e}")

    async def resume(self, chat_id: int):
        try:
            await self.call.resume_stream(chat_id)
        except Exception as e:
            logger.error(f"Resume error for {chat_id}: {e}")

    async def change_volume(self, chat_id: int, volume: int):
        try:
            await self.call.change_volume_call(chat_id, volume)
        except Exception as e:
            logger.error(f"Volume change error for {chat_id}: {e}")


class AssistantManager:
    def __init__(self, sessions: list[str], api_id: int, api_hash: str):
        self.assistants: list[AssistantClient] = [
            AssistantClient(s, i, api_id, api_hash)
            for i, s in enumerate(sessions)
            if s
        ]
        self._chat_map: dict[int, int] = {}  # chat_id → assistant index
        self._round_robin = 0

    async def start_all(self):
        for a in self.assistants:
            try:
                await a.start()
            except Exception as e:
                logger.error(f"Failed to start assistant {a.index}: {e}")

    async def stop_all(self):
        for a in self.assistants:
            await a.stop()

    def _available_assistants(self) -> list[AssistantClient]:
        return [a for a in self.assistants if a.available]

    def assign(self, chat_id: int) -> Optional[AssistantClient]:
        avail = self._available_assistants()
        if not avail:
            return None
        if chat_id in self._chat_map:
            idx = self._chat_map[chat_id]
            for a in avail:
                if a.index == idx:
                    return a
        # Round-robin assignment
        a = avail[self._round_robin % len(avail)]
        self._round_robin += 1
        self._chat_map[chat_id] = a.index
        return a

    def get(self, chat_id: int) -> Optional[AssistantClient]:
        if chat_id in self._chat_map:
            idx = self._chat_map[chat_id]
            for a in self.assistants:
                if a.index == idx and a.available:
                    return a
        return self.assign(chat_id)

    def release(self, chat_id: int):
        self._chat_map.pop(chat_id, None)

    async def health_check_loop(self):
        while True:
            await asyncio.sleep(60)
            for a in self.assistants:
                alive = await a.ping()
                if not alive and a.available:
                    logger.warning(f"Assistant {a.index} unresponsive, marking unavailable")
                    a.available = False
                    # Reassign chats that were using this assistant
                    for chat_id, idx in list(self._chat_map.items()):
                        if idx == a.index:
                            del self._chat_map[chat_id]
                elif alive and not a.available:
                    logger.info(f"Assistant {a.index} recovered")
                    a.available = True
                elif not alive and not a.available:
                    # Try to restart unresponsive assistant
                    logger.info(f"Attempting to restart assistant {a.index}")
                    try:
                        await a.stop()
                        await a.start()
                        if await a.ping():
                            logger.info(f"Assistant {a.index} restarted successfully")
                            a.available = True
                    except Exception as e:
                        logger.error(f"Failed to restart assistant {a.index}: {e}")

    # ── High-level play interface ─────────────────────────────────────

    async def play_audio(self, chat_id: int, stream_url: str, ffmpeg_args: list[str] = None) -> bool:
        assistant = self.get(chat_id)
        if not assistant:
            logger.error(f"No available assistant for chat {chat_id}")
            return False
        try:
            await assistant.play_audio(chat_id, stream_url, ffmpeg_args)
            return True
        except Exception as e:
            logger.error(f"Play audio error for {chat_id}: {e}")
            return False

    async def play_video(self, chat_id: int, stream_url: str) -> bool:
        assistant = self.get(chat_id)
        if not assistant:
            return False
        try:
            await assistant.play_video(chat_id, stream_url)
            return True
        except Exception as e:
            logger.error(f"Play video error for {chat_id}: {e}")
            return False

    async def change_stream(self, chat_id: int, stream_url: str, ffmpeg_args: list[str] = None) -> bool:
        assistant = self.get(chat_id)
        if not assistant:
            return False
        try:
            await assistant.change_stream(chat_id, stream_url, ffmpeg_args)
            return True
        except Exception as e:
            logger.error(f"Change stream error for {chat_id}: {e}")
            return False

    async def pause(self, chat_id: int):
        assistant = self.get(chat_id)
        if assistant:
            await assistant.pause(chat_id)

    async def resume(self, chat_id: int):
        assistant = self.get(chat_id)
        if assistant:
            await assistant.resume(chat_id)

    async def leave_vc(self, chat_id: int):
        assistant = self.get(chat_id)
        if assistant:
            await assistant.leave_vc(chat_id)
        self.release(chat_id)

    async def change_volume(self, chat_id: int, volume: int):
        assistant = self.get(chat_id)
        if assistant:
            await assistant.change_volume(chat_id, volume)
