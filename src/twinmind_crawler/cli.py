"""CLI entry point for twinmind-crawler."""

import argparse
import logging
import sys
from pathlib import Path


def cmd_auth(args):
    from .auth import browser_auth
    browser_auth()


def cmd_list(args):
    from .api import TwinmindAPI
    from .exporter import list_memories

    api = TwinmindAPI()
    list_memories(api)


def cmd_download(args):
    from .api import TwinmindAPI
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
        prog="twinmind-crawler",
        description="Download meeting transcripts and summaries from Twinmind",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable debug logging"
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # auth
    subparsers.add_parser("auth", help="Sign in with Google (opens browser)")

    # list
    subparsers.add_parser("list", help="List all memories without downloading")

    # download
    dl = subparsers.add_parser("download", help="Download memories")
    dl.add_argument(
        "-o", "--output", default="twinmind-export", help="Output directory"
    )
    dl.add_argument(
        "--audio", action="store_true", help="Also download audio files"
    )
    dl.add_argument(
        "--incremental", action="store_true",
        help="Only download new/changed memories",
    )
    dl.add_argument(
        "--force", action="store_true", help="Force re-download all memories"
    )
    dl.add_argument(
        "--since", help="Only download memories after this date (YYYY-MM-DD)"
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    commands = {
        "auth": cmd_auth,
        "list": cmd_list,
        "download": cmd_download,
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
