import dataclasses
import io
import os
import wave
from dataclasses import dataclass

import fal_client
from livekit.agents import stt
from livekit.agents.stt import SpeechEventType, STTCapabilities
from livekit.agents.utils import AudioBuffer, merge_frames

from .log import logger


@dataclass
class _STTOptions:
    language: str
    task: str
    chunk_level: str
    version: str


class WizperSTT(stt.STT):
    def __init__(
        self,
        *,
        language="en",
        task="transcribe",
        chunk_level="segment",
        version="3",
        api_key=None,
    ):
        super().__init__(
            capabilities=STTCapabilities(streaming=False, interim_results=True)
        )
        self._api_key = api_key or os.getenv("FAL_KEY")
        self._opts = _STTOptions(
            language=language, task=task, chunk_level=chunk_level, version=version
        )

        if not self._api_key:
            raise ValueError(
                "FAL AI API key is required. It should be set with env FAL_API_KEY"
            )

    def _sanitize_options(
        self,
        *,
        language: str | None = None,
        task: str | None = None,
        chunk_level: str | None = None,
        version: str | None = None,
    ) -> _STTOptions:
        config = dataclasses.replace(self._opts)
        config.language = language or config.language
        config.task = task or config.task
        config.chunk_level = chunk_level or config.chunk_level
        config.version = version or config.version
        return config

    def _convert_audio_to_wav(self, buffer: AudioBuffer) -> bytes:
        """Convert AudioBuffer to WAV format bytes."""
        io_buffer = io.BytesIO()
        merged_buffer = merge_frames(buffer)

        with wave.open(io_buffer, "wb") as wav:
            wav.setnchannels(merged_buffer.num_channels)
            wav.setsampwidth(2)  # 16-bit
            wav.setframerate(merged_buffer.sample_rate)
            wav.writeframes(bytes(merged_buffer.data))

        return io_buffer.getvalue()

    async def _recognize_impl(
        self,
        buffer: AudioBuffer,
        *,
        language: str | None = None,
        task: str | None = None,
        chunk_level: str | None = None,
        version: str | None = None,
    ) -> stt.SpeechEvent:
        logger.debug("Starting recognition process.")
        try:
            if buffer is None:
                raise ValueError("AudioBuffer input is required")

            config = self._sanitize_options(
                language=language, task=task, chunk_level=chunk_level, version=version
            )

            wav_bytes = self._convert_audio_to_wav(buffer)
            result = await fal_client.run_async(
                "fal-ai/wizper",
                arguments={
                    "audio_url": fal_client.encode(wav_bytes, "audio/x-wav"),
                    "task": config.task,
                    "language": config.language,
                    "chunk_level": config.chunk_level,
                    "version": config.version,
                },
            )
            text = result.get("text", "")
            return self._transcription_to_speech_event(text=text)
        except Exception:
            logger.exception("Error during recognition")
            return self._transcription_to_speech_event(text="")

    def _transcription_to_speech_event(
        self, event_type=SpeechEventType.FINAL_TRANSCRIPT, text=None
    ) -> stt.SpeechEvent:
        return stt.SpeechEvent(
            type=event_type,
            alternatives=[stt.SpeechData(text=text, language=self._opts.language)],
        )
