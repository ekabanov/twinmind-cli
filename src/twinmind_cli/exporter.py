"""Export Twinmind memories to organized local files."""

import json
import logging
import re
from datetime import datetime, timezone
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


def _parse_date(ts) -> datetime | None:
    if ts is None:
        return None
    try:
        if isinstance(ts, (int, float)):
            return datetime.fromtimestamp(ts, tz=timezone.utc)
        return datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
    except (ValueError, OSError):
        return None


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


def filter_by_date(titles: list[MemoryTitle], since: str) -> list[MemoryTitle]:
    """Filter memory titles by creation date."""
    since_dt = datetime.fromisoformat(since).replace(tzinfo=timezone.utc)
    filtered = []
    for t in titles:
        created = _parse_date(t.time_created)
        if created is None or created >= since_dt:
            filtered.append(t)
    return filtered


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

    print("Fetching memory list...")
    titles = api.get_memory_titles()
    print(f"Found {len(titles)} memories.")

    if not titles:
        print("No memories found.")
        return

    if since:
        titles = filter_by_date(titles, since)
        print(f"Filtered to {len(titles)} memories since {since}.")

    index_entries = []
    exported = 0
    skipped = 0

    for i, title in enumerate(titles, 1):
        memory_id = title.id
        dir_name = _memory_dir_name(title)

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

        (mem_dir / "metadata.json").write_text(
            json.dumps(memory.raw_response, indent=2, default=str)
        )

        if memory.summary:
            (mem_dir / "summary.md").write_text(memory.summary)
        if memory.action_items:
            (mem_dir / "action_items.md").write_text(memory.action_items)
        if memory.transcript:
            (mem_dir / "transcript.txt").write_text(memory.transcript)

        if include_audio and memory.has_audio:
            audio_url = api.get_audio_url(memory_id)
            if audio_url:
                audio_ext = "m4a"
                if ".mp3" in audio_url:
                    audio_ext = "mp3"
                elif ".wav" in audio_url:
                    audio_ext = "wav"
                audio_path = mem_dir / f"audio.{audio_ext}"
                print("  Downloading audio...")
                api.download_audio(audio_url, str(audio_path))

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

    index = {
        "exported_at": datetime.now().isoformat(),
        "total_memories": len(titles),
        "exported_count": exported,
        "memories": index_entries,
    }
    (output_dir / "index.json").write_text(json.dumps(index, indent=2, default=str))
    _save_sync_state(output_dir, sync_state)

    print(f"\nDone! Exported {exported} memories, skipped {skipped}.")
    print(f"Output: {output_dir.resolve()}")
