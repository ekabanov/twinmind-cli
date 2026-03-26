"""Data models for Twinmind API responses."""

from dataclasses import dataclass, field


@dataclass
class MemoryTitle:
    """Lightweight memory info from the titles listing endpoint."""

    id: str
    title: str
    summary_id: str = ""
    start_time: str | None = None
    end_time: str | None = None
    time_created: str | None = None
    date_modified: str | None = None
    duration_seconds: float | None = None
    has_audio: bool = False
    metadata: dict = field(default_factory=dict)

    @classmethod
    def from_api(cls, data: dict) -> "MemoryTitle":
        meta = data.get("metadata", {})
        return cls(
            id=data.get("meeting_id") or data.get("id", ""),
            title=data.get("title", "Untitled"),
            summary_id=data.get("summary_id", ""),
            start_time=data.get("start_time"),
            end_time=data.get("end_time"),
            time_created=data.get("time_created"),
            date_modified=data.get("date_modified"),
            duration_seconds=meta.get("durationSeconds"),
            has_audio=data.get("hasAudio", False),
            metadata=meta,
        )


@dataclass
class Memory:
    """Full memory from get_memory endpoint.

    The API nests the memory data under memories[0].summary with keys:
    meeting_title, summary (markdown), transcript (plain text),
    action (action items), attendees, start_time, end_time, etc.
    """

    id: str
    title: str
    summary: str
    transcript: str
    action_items: str
    attendees: str
    start_time: str | None = None
    end_time: str | None = None
    time_created: str | None = None
    date_modified: str | None = None
    duration_seconds: float | None = None
    has_audio: bool = False
    is_audio_transcribe: bool = False
    raw_response: dict = field(default_factory=dict)

    @classmethod
    def from_api(cls, data: dict) -> "Memory":
        meta = data.get("metadata", {})
        return cls(
            id=data.get("meeting_id") or data.get("id", ""),
            title=data.get("meeting_title") or data.get("title", "Untitled"),
            summary=data.get("summary", "") if isinstance(data.get("summary"), str) else "",
            transcript=data.get("transcript", "") if isinstance(data.get("transcript"), str) else "",
            action_items=data.get("action", "") if isinstance(data.get("action"), str) else "",
            attendees=data.get("attendees", "") if isinstance(data.get("attendees"), str) else "",
            start_time=data.get("start_time"),
            end_time=data.get("end_time"),
            time_created=data.get("time_created"),
            date_modified=data.get("date_modified"),
            duration_seconds=meta.get("durationSeconds"),
            has_audio=data.get("hasAudio", False),
            is_audio_transcribe=data.get("is_audio_transcribe", False),
            raw_response=data,
        )
