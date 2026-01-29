"""
Voice Memo Transcription Pipeline

Transcribes voice recordings using LiteLLM's unified transcription interface
(supporting Whisper via OpenAI, Azure, Groq, Deepgram, etc.) and optionally
expands the raw transcript into a structured, well-formatted note.

Features:
- LiteLLM transcription (unified interface to multiple providers)
- Supports: openai, azure, vertex_ai, gemini, deepgram, groq, fireworks_ai
- Optional LLM expansion (fixes transcription errors, adds structure)
- Automatic title generation
- Original transcript preserved as annotation
- Cost tracking for all API calls

See: https://docs.litellm.ai/docs/audio_transcription

Usage:
    from app.pipelines import VoiceTranscriber

    transcriber = VoiceTranscriber()
    content = await transcriber.process(Path("voice_memo.mp3"))
"""

import json
import logging
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import litellm
from litellm import transcription
from mutagen import File as MutagenFile

from app.config.settings import settings
from app.models.content import (
    Annotation,
    AnnotationType,
    ContentType,
    UnifiedContent,
)
from app.pipelines.base import BasePipeline, PipelineInput, PipelineContentType
from app.enums.pipeline import PipelineName, PipelineOperation
from app.models.llm_usage import (
    LLMUsage,
    extract_provider,
    create_error_usage,
)
from app.enums.pipeline import PipelineOperation
from app.services.llm import get_llm_client, build_messages
from app.services.cost_tracking import CostTracker

logger = logging.getLogger(__name__)

# Configure LiteLLM logging (set_verbose is deprecated)
if settings.DEBUG:
    os.environ["LITELLM_LOG"] = "DEBUG"

# =============================================================================
# Constants
# =============================================================================

# Transcript processing
MIN_TRANSCRIPT_LENGTH_FOR_EXPANSION = (
    20  # Characters - skip expansion for very short transcripts
)

# Title constraints
MAX_TITLE_LENGTH = 100  # Maximum characters for title
TITLE_TRUNCATE_SUFFIX = "..."
TITLE_LOG_PREVIEW_LENGTH = 50  # Characters to show in log messages

# LLM parameters for note expansion
EXPANSION_MAX_TOKENS = 4000  # Allow for expanded content
EXPANSION_TEMPERATURE = 0.3  # Lower temp for more faithful reproduction

# Time formatting
SECONDS_PER_MINUTE = 60
SECONDS_PER_HOUR = 3600

# Date/time formats
DATETIME_FORMAT = "%Y-%m-%d %H:%M"
DEFAULT_TITLE_PREFIX = "Voice memo"


@dataclass
class ExpandedNote:
    """Result from note expansion containing both title and content."""

    title: str
    content: str


class VoiceTranscriber(BasePipeline):
    """
    Voice memo transcription pipeline using LiteLLM.

    Uses LiteLLM's unified transcription interface to support multiple
    providers (OpenAI, Azure, Groq, Deepgram, etc.) with the same code.
    Tracks LLM costs for all API calls.

    Supported providers (via LiteLLM):
    - openai: whisper-1
    - azure: azure/whisper
    - groq: groq/whisper-large-v3
    - deepgram: deepgram/nova-2

    Routing:
    - Content type: PipelineContentType.VOICE_MEMO
    - File formats: .mp3, .mp4, .mpeg, .mpga, .m4a, .wav, .webm, .ogg, .flac
    """

    SUPPORTED_FORMATS = {
        ".mp3",
        ".mp4",
        ".mpeg",
        ".mpga",
        ".m4a",
        ".wav",
        ".webm",
        ".ogg",
        ".flac",
    }
    SUPPORTED_CONTENT_TYPES = {PipelineContentType.VOICE_MEMO}
    PIPELINE_NAME = PipelineName.VOICE_TRANSCRIBE

    def __init__(
        self,
        whisper_model: str = "whisper-1",
        text_model: Optional[str] = None,
        expand_notes: bool = True,
        track_costs: bool = True,
    ):
        """
        Initialize voice transcriber.

        Args:
            whisper_model: LiteLLM model identifier for transcription
                          e.g., "whisper-1" (OpenAI), "groq/whisper-large-v3"
            text_model: Text model for note expansion
            expand_notes: Whether to expand transcript into structured note
            track_costs: Whether to log LLM costs to database
        """
        super().__init__()
        self.whisper_model = whisper_model
        self.text_model = text_model  # Optional text model for note expansion
        self.expand_notes = expand_notes
        self.track_costs = track_costs
        self._usage_records: list[LLMUsage] = []

    def supports(self, input_data: PipelineInput) -> bool:
        """
        Check if this pipeline can handle the input.

        Requires:
        - content_type == VOICE_MEMO
        - path is set and has supported audio extension
        """
        if not isinstance(input_data, PipelineInput):
            return False

        if input_data.content_type != PipelineContentType.VOICE_MEMO:
            return False

        if input_data.path is None:
            return False

        return input_data.path.suffix.lower() in self.SUPPORTED_FORMATS

    async def process(
        self,
        input_data: PipelineInput,
        expand: Optional[bool] = None,
        content_id: Optional[str] = None,
    ) -> UnifiedContent:
        """
        Transcribe audio file from PipelineInput.

        Args:
            input_data: PipelineInput with path to audio file
            expand: Override default expand_notes setting
            content_id: Optional content ID for cost attribution

        Returns:
            UnifiedContent with transcription
        """
        if input_data.path is None:
            raise ValueError("PipelineInput.path is required for voice transcription")

        return await self.process_path(input_data.path, expand, content_id)

    async def process_path(
        self,
        audio_path: Path,
        expand: Optional[bool] = None,
        content_id: Optional[str] = None,
    ) -> UnifiedContent:
        """
        Transcribe audio file (direct path interface).

        Args:
            audio_path: Path to audio file
            expand: Override default expand_notes setting
            content_id: Optional content ID for cost attribution

        Returns:
            UnifiedContent with transcription
        """
        audio_path = Path(audio_path)

        # Reset usage records for this processing run
        self._usage_records = []
        self._content_id = content_id

        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        self.logger.info(f"Transcribing: {audio_path}")

        # Calculate hash for metadata (deduplication is handled at capture layer)
        file_hash = self.calculate_hash(audio_path)

        # Get actual audio duration
        duration_seconds = self._get_audio_duration(audio_path)

        # Transcribe with Whisper
        transcript = await self._transcribe(audio_path)

        self.logger.info(f"Transcribed: {len(transcript)} characters")

        # Optionally expand into structured note with LLM-generated title
        should_expand = expand if expand is not None else self.expand_notes

        if should_expand and transcript and self.text_model:
            expanded_note = await self._expand_note(transcript)
            title = expanded_note.title
            content = expanded_note.content
        else:
            # Fallback: use transcript as-is with timestamp title
            title = (
                f"{DEFAULT_TITLE_PREFIX} - {datetime.now(timezone.utc).strftime(DATETIME_FORMAT)}"
            )
            content = transcript

        # Get file modification time as creation time
        created_at = datetime.fromtimestamp(audio_path.stat().st_mtime)

        # Log all accumulated LLM costs to database
        if self.track_costs and self._usage_records:
            total_cost = sum(u.cost_usd or 0 for u in self._usage_records)
            self.logger.info(
                f"Voice transcription complete - Total LLM cost: ${total_cost:.4f} "
                f"({len(self._usage_records)} API calls)"
            )
            await CostTracker.log_usages_batch(self._usage_records)

        return UnifiedContent(
            source_type=ContentType.VOICE_MEMO,
            source_file_path=str(audio_path),
            title=title,
            created_at=created_at,
            full_text=content,
            annotations=[
                Annotation(
                    type=AnnotationType.TYPED_COMMENT,
                    content=f"Original transcript: {transcript}",
                )
            ],
            raw_file_hash=file_hash,
            asset_paths=[str(audio_path)],
            metadata={
                "original_transcript": transcript,
                "expanded": should_expand and self.text_model is not None,
                "duration_seconds": duration_seconds,
                "duration_formatted": self._format_duration(duration_seconds),
                "llm_cost_usd": sum(u.cost_usd or 0 for u in self._usage_records),
                "llm_api_calls": len(self._usage_records),
            },
        )

    async def _transcribe(self, audio_path: Path) -> str:
        """Transcribe audio file using LiteLLM's unified transcription API."""
        start_time = time.perf_counter()

        try:
            with open(audio_path, "rb") as audio_file:
                # LiteLLM's transcription function (runs sync, but is fast for audio)
                # Note: LiteLLM transcription is currently sync-only, but audio
                # uploads are I/O-bound anyway
                response = transcription(
                    model=self.whisper_model,
                    file=audio_file,
                )

            latency_ms = int((time.perf_counter() - start_time) * 1000)

            # Extract transcribed text
            transcript_text = (
                response.text if hasattr(response, "text") else str(response)
            )

            # Track usage/cost
            usage = self._extract_transcription_usage(
                response=response,
                latency_ms=latency_ms,
            )
            self._usage_records.append(usage)

            if usage.cost_usd:
                logger.info(
                    f"Transcription [{self.whisper_model}] - "
                    f"Cost: ${usage.cost_usd:.4f}, "
                    f"Latency: {usage.latency_ms}ms"
                )

            return transcript_text.strip()

        except Exception as e:
            latency_ms = int((time.perf_counter() - start_time) * 1000)
            error_usage = create_error_usage(
                model=self.whisper_model,
                request_type="transcription",
                latency_ms=latency_ms,
                error_message=str(e),
                pipeline=self.PIPELINE_NAME,
                content_id=getattr(self, "_content_id", None),
                operation=PipelineOperation.AUDIO_TRANSCRIPTION,
            )
            self._usage_records.append(error_usage)
            logger.error(f"Transcription failed with {self.whisper_model}: {e}")
            raise

    def _extract_transcription_usage(
        self,
        response,
        latency_ms: int,
    ) -> LLMUsage:
        """Extract usage information from transcription response."""
        usage = LLMUsage(
            model=self.whisper_model,
            provider=extract_provider(self.whisper_model),
            request_type="transcription",
            latency_ms=latency_ms,
            pipeline=self.PIPELINE_NAME,
            content_id=getattr(self, "_content_id", None),
            operation=PipelineOperation.AUDIO_TRANSCRIPTION,
        )

        # LiteLLM transcription responses may have usage info
        if hasattr(response, "usage") and response.usage:
            usage.prompt_tokens = getattr(response.usage, "prompt_tokens", None)
            usage.completion_tokens = getattr(response.usage, "completion_tokens", None)
            usage.total_tokens = getattr(response.usage, "total_tokens", None)

        # Extract cost from LiteLLM's hidden params if available
        if hasattr(response, "_hidden_params") and response._hidden_params:
            hidden = response._hidden_params
            usage.cost_usd = hidden.get("response_cost")

            if "additional_args" in hidden:
                additional = hidden["additional_args"]
                usage.input_cost_usd = additional.get("input_cost")
                usage.output_cost_usd = additional.get("output_cost")

        return usage

    async def _expand_note(self, transcript: str) -> ExpandedNote:
        """Expand raw transcript into a well-structured note with title.

        Uses an LLM to:
        - Generate a concise, descriptive title
        - Fix transcription errors (misheard words, punctuation)
        - Add structure (headings, bullet points, paragraphs)
        - Preserve the original meaning and intent
        - Remove filler words and false starts

        Args:
            transcript: Raw transcript from speech-to-text

        Returns:
            ExpandedNote with title and content
        """
        if (
            not transcript
            or len(transcript.strip()) < MIN_TRANSCRIPT_LENGTH_FOR_EXPANSION
        ):
            self.logger.debug("Note expansion skipped - transcript too short")
            return ExpandedNote(
                title=f"{DEFAULT_TITLE_PREFIX} - {datetime.now(timezone.utc).strftime(DATETIME_FORMAT)}",
                content=transcript,
            )

        system_prompt = """You are an expert note-taking assistant that transforms raw voice transcripts into clean, well-structured notes.

Your task:
1. Generate a concise, descriptive title (max 80 chars) that captures the main topic
2. Fix obvious transcription errors (misheard words, missing punctuation)
3. Remove filler words (um, uh, like, you know) and false starts
4. Organize the content with clear structure:
   - Break into paragraphs for readability
   - Use bullet points for lists or action items
   - Use headers (##) for distinct topics if the note covers multiple subjects
5. Preserve the original meaning, intent, and personality
6. Keep technical terms, names, and specific details accurate
7. If action items or todos are mentioned, format them clearly

You MUST respond with valid JSON in this exact format:
{
  "title": "A concise descriptive title",
  "content": "The cleaned up note content in Markdown format"
}

Do NOT include any text outside the JSON object."""

        user_prompt = f"""Transform this voice transcript into a structured note with title.

TRANSCRIPT:
---
{transcript}
---

Respond with JSON containing "title" and "content" fields only."""

        try:
            self.logger.debug(f"Expanding note with {self.text_model}")

            client = get_llm_client()
            messages = build_messages(user_prompt, system_prompt)
            response_text, usage = await client.complete(
                operation=PipelineOperation.NOTE_EXPANSION,
                messages=messages,
                model=self.text_model,
                max_tokens=EXPANSION_MAX_TOKENS,
                temperature=EXPANSION_TEMPERATURE,
                json_mode=True,
                pipeline=self.PIPELINE_NAME,
                content_id=getattr(self, "_content_id", None),
            )

            # Track the usage
            self._usage_records.append(usage)

            # Parse the JSON response
            try:
                result = json.loads(response_text)
                title = result.get("title", "").strip()
                content = result.get("content", "").strip()

                # Validate we got both fields
                if not title:
                    title = f"{DEFAULT_TITLE_PREFIX} - {datetime.now(timezone.utc).strftime(DATETIME_FORMAT)}"
                if not content:
                    content = transcript

                # Truncate title if too long
                if len(title) > MAX_TITLE_LENGTH:
                    truncate_at = MAX_TITLE_LENGTH - len(TITLE_TRUNCATE_SUFFIX)
                    title = title[:truncate_at] + TITLE_TRUNCATE_SUFFIX

            except json.JSONDecodeError as e:
                self.logger.warning(f"Failed to parse JSON response: {e}")
                # Fall back to using response as content
                title = f"{DEFAULT_TITLE_PREFIX} - {datetime.now(timezone.utc).strftime(DATETIME_FORMAT)}"
                content = response_text.strip()

            self.logger.info(
                f"Note expansion complete - "
                f"Title: '{title[:TITLE_LOG_PREVIEW_LENGTH]}...', "
                f"Input: {len(transcript)} chars, Output: {len(content)} chars"
            )

            return ExpandedNote(title=title, content=content)

        except Exception as e:
            self.logger.warning(
                f"Note expansion failed with {self.text_model}: {e}. "
                "Returning original transcript."
            )
            # Return original transcript on failure - don't lose the content
            return ExpandedNote(
                title=f"{DEFAULT_TITLE_PREFIX} - {datetime.now(timezone.utc).strftime(DATETIME_FORMAT)}",
                content=transcript,
            )

    def _get_audio_duration(self, audio_path: Path) -> Optional[float]:
        """Get actual audio duration in seconds using mutagen.

        Args:
            audio_path: Path to the audio file

        Returns:
            Duration in seconds, or None if unable to read
        """
        try:
            audio = MutagenFile(audio_path)
            if audio is not None and audio.info is not None:
                return audio.info.length
        except Exception as e:
            self.logger.warning(f"Could not read audio duration from {audio_path}: {e}")

        return None

    def _format_duration(self, seconds: Optional[float]) -> str:
        """Format duration in seconds to human-readable string.

        Args:
            seconds: Duration in seconds

        Returns:
            Formatted string like "2:34" or "1:02:15"
        """
        if seconds is None:
            return "unknown"

        total_seconds = int(seconds)
        hours = total_seconds // SECONDS_PER_HOUR
        minutes = (total_seconds % SECONDS_PER_HOUR) // SECONDS_PER_MINUTE
        secs = total_seconds % SECONDS_PER_MINUTE

        if hours > 0:
            return f"{hours}:{minutes:02d}:{secs:02d}"
        else:
            return f"{minutes}:{secs:02d}"
