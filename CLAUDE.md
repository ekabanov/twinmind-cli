# Twinmind CLI

CLI tool and Claude Code skill for accessing Twinmind meeting transcripts, summaries, and action items.

## Project Setup

```bash
# Install (requires uv)
uv venv --python 3.13 && uv pip install -e .

# First-time auth
twinmind auth

# Or set env var for automation
export TWINMIND_REFRESH_TOKEN="your-refresh-token"
```

## Architecture

- **Twinmind Frontend**: Next.js app at `app.twinmind.com`
- **Backend API**: `https://api.thirdear.live` ("Third Ear" is the original product name)
- **Authentication**: Firebase Auth with Google sign-in
- **Package**: `src/twinmind_cli/` — Python 3.11+, installed as `twinmind` CLI

## Twinmind API Reference

### Authentication

- **Firebase API Key**: `AIzaSyD2Sd_NP3vA4rwvoroKqDefpXZeCMDXcIQ`
- **Firebase Tenant ID**: `PRODTwinMind-dcnoy`
- All API requests require `Authorization: Bearer <firebase_id_token>`
- ID tokens expire after 1 hour, refreshed via Firebase token endpoint

**Token refresh:**
```
POST https://securetoken.googleapis.com/v1/token?key=AIzaSyD2Sd_NP3vA4rwvoroKqDefpXZeCMDXcIQ
Content-Type: application/x-www-form-urlencoded

grant_type=refresh_token&refresh_token=<REFRESH_TOKEN>
```

Response: `{ "id_token": "...", "refresh_token": "...", "expires_in": "3600" }`

### Endpoints

All endpoints use **POST** method with JSON body. Base URL: `https://api.thirdear.live`

#### POST /api/v1/get_memory_titles

Lists all memories (meetings).

- **Request**: `{}` (empty JSON body)
- **Response**:
```json
{
  "memories": [
    {
      "title": "Meeting Title",
      "meeting_id": "A5F92C56-6207-407F-A536-155671B46001",
      "summary_id": "A5F92C56-6207-407F-A536-155671B46001",
      "start_time": "2026-03-25T09:34:31.000Z",
      "end_time": "2026-03-25T10:23:17.000Z",
      "time_created": "2026-03-25T10:24:28.120Z",
      "date_modified": "2026-03-26T10:31:35.587Z",
      "metadata": {
        "durationSeconds": 2926,
        "calendarJSON": "",
        "durationMs": 48,
        "deviceType": "iPhone"
      },
      "hasAudio": false
    }
  ]
}
```

#### POST /api/v1/get_memory

Fetches full memory with transcript, summary, and action items.

- **Request**: `{"meeting_id": "<UUID>"}`
- **Response** (nested structure):
```json
{
  "memories": [
    {
      "summary": {
        "keywords": "...",
        "meeting_title": "Meeting Title",
        "summary": "## Markdown Summary\n\n- Bullet points...",
        "action": "* [ ] Action item 1\n* [ ] Action item 2",
        "transcript": "11:34 Speaker text here...\n11:35 More text...",
        "attendees": "",
        "time_created": "2026-03-25T10:24:28.120Z",
        "meeting_id": "A5F92C56-...",
        "summary_id": "A5F92C56-...",
        "share": "...",
        "start_time": "2026-03-25T09:34:31.000Z",
        "end_time": "2026-03-25T10:23:17.000Z",
        "start_time_local": "...",
        "end_time_local": "...",
        "metadata": { "durationSeconds": 2926, "deviceType": "iPhone" },
        "version": "...",
        "is_deleted": false,
        "status": "...",
        "date_modified": "2026-03-26T10:31:35.587Z",
        "hasAudio": false,
        "is_audio_transcribe": false
      }
    }
  ]
}
```

Key fields inside `memories[0].summary`:
- `summary` — Markdown-formatted meeting summary
- `transcript` — Plain text transcript with timestamps
- `action` — Action items as markdown checklist
- `meeting_title` — Title
- `attendees` — Attendee list (may be empty)

#### POST /api/v2/summary/view

Richer summary view (V2 endpoint).

- **Request**: `{"meeting_id": "<UUID>"}`

#### POST /api/v2/transcriber-proxy/get-audio-url

Get signed URL for audio download.

- **Request**: `{"meeting_id": "<UUID>"}`
- **Response**: `{"url": "https://signed-url..."}`

### Other Known Endpoints

| Endpoint | Purpose |
|----------|---------|
| `POST /api/v1/get_chat_history` | Chat history |
| `POST /api/v1/add_summary` | Add summary |
| `POST /api/v1/edit_summary` | Edit summary |
| `DELETE /api/v1/delete_summary` | Delete summary |
| `POST /api/v1/add_notes` | Add notes |
| `POST /api/v2/summary/share` | Share summary |
| `POST /api/v2/summary-split/auto-split` | Auto-split transcript |
| `POST /api/v2/summary-split/generate-summaries` | Generate summaries |
| `POST /api/v2/summary-split/transcript-chunk` | Get transcript chunk |
| `POST /api/v2/llm/summary` | LLM summary generation |
| `POST /api/v2/custom-templates` | CRUD custom templates |
| `POST /api/v2/personalization` | User settings |
| `POST /api/v2/todo-lists` | Todo lists |
| `POST /api/py/twinmind/chrome` | Chrome chat endpoint |

## Auth Token Storage

- **File**: `~/.twinmind-cli/auth.json`
- **Env var**: `TWINMIND_REFRESH_TOKEN` (takes priority over file)
- **Browser extraction**: `extract-token.js` scans localStorage + IndexedDB on app.twinmind.com

## CLI Commands

```bash
twinmind auth                                # Interactive auth setup
twinmind list [--since DATE] [--limit N] [--json]  # List memories
twinmind show <meeting_id> [--json]          # Show single memory
twinmind export [--since] [--audio] [--incremental] [-o DIR]  # Bulk export
```
