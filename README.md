# twinmind-cli

CLI tool for accessing [Twinmind](https://app.twinmind.com) meeting transcripts, summaries, and action items. Also includes a Claude Code skill for AI-assisted meeting queries.

## Installation

Requires [uv](https://docs.astral.sh/uv/) and Python 3.11+.

```bash
git clone https://github.com/ekabanov/twinmind-cli.git
cd twinmind-cli
uv venv --python 3.13
uv pip install -e .
```

## Authentication

Twinmind uses Firebase Auth with Google sign-in. Set up credentials with:

```bash
twinmind auth
```

This opens a browser for Google sign-in and stores the refresh token at `~/.twinmind-cli/auth.json`.

Alternatively, set the token directly as an environment variable:

```bash
export TWINMIND_REFRESH_TOKEN="your-refresh-token"
```

### Extracting a token from the browser

If you're already logged into app.twinmind.com, you can extract your refresh token by running `extract-token.js` in the browser console. It copies the token to your clipboard.

## Usage

### List meetings

```bash
twinmind list                       # List all meetings
twinmind list --since 2026-01-01    # Filter by date
twinmind list --limit 10            # Limit results
twinmind list --json                # JSON output
```

### Show a meeting

```bash
twinmind show <meeting_id>          # Display summary, action items, transcript
twinmind show <meeting_id> --json   # JSON output
```

### Export meetings

```bash
twinmind export                          # Export all to ./twinmind-export/
twinmind export -o ~/meetings            # Custom output directory
twinmind export --incremental            # Only new/changed meetings
twinmind export --audio                  # Include audio files
twinmind export --since 2026-01-01       # Filter by date
twinmind export --force                  # Re-download everything
```

### Other options

```bash
twinmind -v <command>               # Verbose/debug logging
```

## Claude Code Skill

This project includes a Claude Code skill (`twinmind`) that lets you query your meetings conversationally:

> "What action items came out of yesterday's meetings?"
> "Summarize my meeting with the design team last week"

The skill is registered automatically when the project is in your Claude Code scope.

## Project Structure

```
src/twinmind_cli/
  api.py       — Twinmind API client
  auth.py      — Firebase authentication
  cli.py       — CLI entry point
  exporter.py  — Bulk export logic
  models.py    — Data models
extract-token.js — Browser helper to extract auth token
twinmind         — Wrapper script (runs via uv without install)
```

## License

MIT
