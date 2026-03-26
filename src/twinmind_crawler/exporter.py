"""Export Twinmind memories to organized local files."""

import json
import logging
import re
import time
from datetime import datetime
from pathlib import Path

from .api import TwinmindAPI
from .models import Memory, MemoryTitle

logger = logging.getLogger(__name__)

DEFAULT_OUTPUT_DIR = Path("twinmind-export")


def slugify(text: str, max_length: int = 60) -> str:
    """Convert text to a filesystem-safe slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    return text[:max_length]


def _format_timestamp(seconds: float | int | None) -> str:
    if seconds is None:
        return "??:??:??"
    s = int(seconds)
    h, remainder = divmod(s, 3600)
    m, sec = divmod(remainder, 60)
    if h > 0:
        return f"{h:02d}:{m:02d}:{sec:02d}"
    return f"{m:02d}:{sec:02d}"


def _extract_transcript_text(transcript_data) -> str:
    """Best-effort extraction of plain text from the transcript tree structure."""
    if transcript_data is None:
        return ""

    lines = []

    def _walk(node, depth=0):
        if isinstance(node, str):
            lines.append(node)
            return

        if isinstance(node, list):
            for item in node:
                _walk(item, depth)
            return

        if isinstance(node, dict):
            # Skip deleted segments
            if node.get("isDeleted"):
                return

            text = node.get("text", "")
            speaker = node.get("speaker") or node.get("speaker_name", "")
            start = node.get("start_time_seconds") or node.get("start_time") or node.get("start")
            timestamp = _format_timestamp(start) if start is not None else None

            if text:
                prefix_parts = []
                if timestamp:
                    prefix_parts.append(f"[{timestamp}]")
                if speaker:
                    prefix_parts.append(f"{speaker}:")
                prefix = " ".join(prefix_parts)
                if prefix:
                    lines.append(f"{prefix} {text}")
                else:
                    lines.append(text)

            # Recurse into children
            for key in ("subChunks", "chunks", "children", "segments"):
                children = node.get(key)
                if children:
                    _walk(children, depth + 1)

    _walk(transcript_data)
    return "\n".join(lines)


def _memory_dir_name(memory: Memory | MemoryTitle) -> str:
    """Generate directory name like 2024-01-15_meeting-title."""
    date_str = "unknown-date"
    for ts_field in [memory.start_time, memory.time_created]:
        if ts_field:
            try:
                if isinstance(ts_field, (int, float)):
                    dt = datetime.fromtimestamp(ts_field)
                else:
                    dt = datetime.fromisoformat(str(ts_field).replace("Z", "+00:00"))
                date_str = dt.strftime("%Y-%m-%d")
                break
            except (ValueError, OSError):
                continue

    slug = slugify(memory.title) or "untitled"
    return f"{date_str}_{slug}"


def _load_sync_state(output_dir: Path) -> dict:
    state_file = output_dir / ".sync_state.json"
    if state_file.exists():
        try:
            return json.loads(state_file.read_text())
        except json.JSONDecodeError:
            pass
    return {"downloaded_memories": {}}


def _save_sync_state(output_dir: Path, state: dict) -> None:
    state_file = output_dir / ".sync_state.json"
    state_file.write_text(json.dumps(state, indent=2))


def export_memories(
    api: TwinmindAPI,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    include_audio: bool = False,
    incremental: bool = False,
    force: bool = False,
    since: str | None = None,
) -> None:
    """Export all memories to the output directory."""
    output_dir = Path(output_dir)
    memories_dir = output_dir / "memories"
    memories_dir.mkdir(parents=True, exist_ok=True)

    sync_state = _load_sync_state(output_dir) if incremental else {"downloaded_memories": {}}

    # Fetch all memory titles
    print("Fetching memory list...")
    titles = api.get_memory_titles()
    print(f"Found {len(titles)} memories.")

    if not titles:
        print("No memories found.")
        return

    # Filter by date if --since specified
    if since:
        from datetime import timezone
        since_dt = datetime.fromisoformat(since).replace(tzinfo=timezone.utc)
        filtered = []
        for t in titles:
            if t.time_created:
                try:
                    ts = t.time_created
                    if isinstance(ts, (int, float)):
                        created = datetime.fromtimestamp(ts)
                    else:
                        created = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
                    if created >= since_dt:
                        filtered.append(t)
                except (ValueError, OSError):
                    filtered.append(t)  # include if we can't parse
            else:
                filtered.append(t)
        print(f"Filtered to {len(filtered)} memories since {since}.")
        titles = filtered

    # Build index
    index_entries = []
    exported = 0
    skipped = 0

    for i, title in enumerate(titles, 1):
        memory_id = title.id
        dir_name = _memory_dir_name(title)

        # Check incremental sync
        if incremental and not force and memory_id in sync_state["downloaded_memories"]:
            stored = sync_state["downloaded_memories"][memory_id]
            if title.date_modified and stored.get("modified_at") == title.date_modified:
                logger.debug("Skipping unchanged memory: %s", title.title)
                skipped += 1
                continue

        print(f"[{i}/{len(titles)}] Downloading: {title.title}")

        try:
            memory = api.get_memory(memory_id)
        except Exception as e:
            logger.error("Failed to fetch memory %s: %s", memory_id, e)
            continue

        mem_dir = memories_dir / dir_name
        mem_dir.mkdir(parents=True, exist_ok=True)

        # Save raw metadata
        (mem_dir / "metadata.json").write_text(
            json.dumps(memory.raw_response, indent=2, default=str)
        )

        # Save summary (markdown format from the API)
        if memory.summary:
            (mem_dir / "summary.md").write_text(memory.summary)

        # Save action items
        if memory.action_items:
            (mem_dir / "action_items.md").write_text(memory.action_items)

        # Save transcript (already plain text from the API)
        if memory.transcript:
            (mem_dir / "transcript.txt").write_text(memory.transcript)

        # Download audio if requested
        if include_audio and memory.has_audio:
            audio_url = api.get_audio_url(memory_id)
            if audio_url:
                audio_ext = "m4a"
                if ".mp3" in audio_url:
                    audio_ext = "mp3"
                elif ".wav" in audio_url:
                    audio_ext = "wav"
                audio_path = mem_dir / f"audio.{audio_ext}"
                print(f"  Downloading audio...")
                api.download_audio(audio_url, str(audio_path))

        # Update sync state
        sync_state["downloaded_memories"][memory_id] = {
            "downloaded_at": datetime.now().isoformat(),
            "modified_at": memory.date_modified,
            "dir_name": dir_name,
        }

        index_entries.append({
            "id": memory_id,
            "title": memory.title,
            "dir_name": dir_name,
            "start_time": memory.start_time,
            "duration": memory.duration_seconds,
            "has_audio": memory.has_audio,
        })

        exported += 1

    # Save index
    index = {
        "exported_at": datetime.now().isoformat(),
        "total_memories": len(titles),
        "exported_count": exported,
        "memories": index_entries,
    }
    (output_dir / "index.json").write_text(json.dumps(index, indent=2, default=str))

    # Save sync state
    _save_sync_state(output_dir, sync_state)

    print(f"\nDone! Exported {exported} memories, skipped {skipped}.")
    print(f"Output: {output_dir.resolve()}")


def list_memories(api: TwinmindAPI) -> list[MemoryTitle]:
    """List all memories without downloading."""
    titles = api.get_memory_titles()
    for t in titles:
        date_str = ""
        if t.time_created:
            try:
                ts = t.time_created
                if isinstance(ts, (int, float)):
                    dt = datetime.fromtimestamp(ts)
                else:
                    dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
                date_str = dt.strftime("%Y-%m-%d %H:%M")
            except (ValueError, OSError):
                date_str = str(t.time_created)

        duration_str = ""
        if t.duration_seconds:
            mins = int(t.duration_seconds) // 60
            duration_str = f" ({mins}m)"

        audio_str = " [audio]" if t.has_audio else ""
        print(f"  {date_str}  {t.title}{duration_str}{audio_str}")

    print(f"\nTotal: {len(titles)} memories")
    return titles
