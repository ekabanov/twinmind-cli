---
name: twinmind
description: Use when the user asks about their meetings, meeting notes, transcripts, summaries, or action items from Twinmind. Queries the twinmind CLI to fetch meeting data.
---

# Twinmind Meeting Data

You have access to the user's Twinmind meeting data via the `twinmind` CLI tool.

## Available Commands

### List meetings
```bash
twinmind list --json
twinmind list --json --since 2026-03-01
twinmind list --json --limit 5
```
Returns JSON array of meetings with: `id`, `title`, `start_time`, `end_time`, `time_created`, `duration_seconds`, `has_audio`.

### Get a specific meeting
```bash
twinmind show <meeting_id> --json
```
Returns JSON with: `id`, `title`, `summary` (markdown), `transcript` (plain text), `action_items` (markdown checklist), `attendees`, timestamps, `duration_seconds`.

### Export meetings to files
```bash
twinmind export --since 2026-03-01 -o ./twinmind-export
```

## How to use

1. **Always use `--json` flag** when fetching data so you can parse it programmatically
2. **Start with `twinmind list --json`** to find relevant meetings by title/date
3. **Then `twinmind show <id> --json`** to get full details of specific meetings
4. Present the data naturally — summarize, answer questions, extract action items, etc.

## Auth errors

If you get an auth error, tell the user to run `twinmind auth` interactively, or set the `TWINMIND_REFRESH_TOKEN` environment variable.

## Example workflow

User asks: "What meetings did I have this week?"

1. Run `twinmind list --json --since 2026-03-20` via Bash
2. Parse the JSON output
3. Present a summary of meetings with titles, dates, and durations

User asks: "What were the action items from my Nvidia meeting?"

1. Run `twinmind list --json` to find the meeting
2. Find the meeting with "Nvidia" in the title
3. Run `twinmind show <id> --json` to get full details
4. Extract and present the `action_items` field
