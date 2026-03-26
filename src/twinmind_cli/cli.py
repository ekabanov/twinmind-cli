"""CLI entry point for twinmind."""

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

from .api import TwinmindAPI
from .exporter import filter_by_date


def cmd_auth(args):
    from .auth import browser_auth
    browser_auth()


def cmd_list(args):
    api = TwinmindAPI()
    titles = api.get_memory_titles()

    if args.since:
        titles = filter_by_date(titles, args.since)

    if args.limit:
        titles = titles[: args.limit]

    if args.json:
        print(json.dumps([t.to_dict() for t in titles], indent=2, default=str))
        return

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
        print(f"  {t.id}  {date_str}  {t.title}{duration_str}{audio_str}")

    print(f"\nTotal: {len(titles)} memories")


def cmd_show(args):
    api = TwinmindAPI()
    memory = api.get_memory(args.meeting_id)

    if args.json:
        print(json.dumps(memory.to_dict(), indent=2, default=str))
        return

    print(f"# {memory.title}")
    print(f"ID: {memory.id}")
    if memory.start_time:
        print(f"Date: {memory.start_time}")
    if memory.duration_seconds:
        print(f"Duration: {int(memory.duration_seconds) // 60}m")
    print()

    if memory.summary:
        print("## Summary")
        print()
        print(memory.summary)
        print()

    if memory.action_items:
        print("## Action Items")
        print()
        print(memory.action_items)
        print()

    if memory.transcript:
        print("## Transcript")
        print()
        print(memory.transcript)


def cmd_export(args):
    from .exporter import export_memories

    api = TwinmindAPI()
    export_memories(
        api,
        output_dir=Path(args.output),
        include_audio=args.audio,
        incremental=args.incremental,
        force=args.force,
        since=args.since,
    )


def main():
    parser = argparse.ArgumentParser(
        prog="twinmind",
        description="CLI for Twinmind meeting transcripts and summaries",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable debug logging"
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # auth
    subparsers.add_parser("auth", help="Sign in with Google (opens browser)")

    # list
    ls = subparsers.add_parser("list", help="List all memories")
    ls.add_argument("--since", help="Only show memories after this date (YYYY-MM-DD)")
    ls.add_argument("--limit", type=int, help="Limit number of results")
    ls.add_argument("--json", action="store_true", help="Output as JSON")

    # show
    sh = subparsers.add_parser("show", help="Show a single memory")
    sh.add_argument("meeting_id", help="Meeting ID to show")
    sh.add_argument("--json", action="store_true", help="Output as JSON")

    # export
    ex = subparsers.add_parser("export", help="Export memories to local files")
    ex.add_argument("-o", "--output", default="twinmind-export", help="Output directory")
    ex.add_argument("--audio", action="store_true", help="Also download audio files")
    ex.add_argument("--incremental", action="store_true", help="Only download new/changed memories")
    ex.add_argument("--force", action="store_true", help="Force re-download all memories")
    ex.add_argument("--since", help="Only download memories after this date (YYYY-MM-DD)")

    args = parser.parse_args()

    # Suppress logging when --json is used to keep output clean
    json_mode = getattr(args, "json", False)
    if json_mode and not args.verbose:
        log_level = logging.WARNING
    elif args.verbose:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO

    logging.basicConfig(level=log_level, format="%(levelname)s: %(message)s")

    commands = {
        "auth": cmd_auth,
        "list": cmd_list,
        "show": cmd_show,
        "export": cmd_export,
    }

    try:
        commands[args.command](args)
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nInterrupted.")
        sys.exit(130)


if __name__ == "__main__":
    main()
