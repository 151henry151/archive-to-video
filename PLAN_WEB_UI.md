# Web UI & Backend – Architecture Plan

**Branch:** `feature/web-ui-backend`  
**Status:** Planning

## Overview

Expose the archive-to-yt workflow as a web backend with API, plus a frontend GUI. Users host on their own server; each user signs into their own YouTube account. The UI mirrors the CLI flow.

## Requirements Summary

- **Backend API** – Expose current logic as HTTP API
- **Web frontend** – GUI for the full workflow
- **Per-user YouTube auth** – Each user authorizes their own channel (no shared account)
- **Flow parity** – Same steps as CLI: URL input → preview → confirm → process → review private → publish public
- **Self-hostable** – Run on user’s webserver
- **Docker** – Single image for easy deployment; nginx reverse-proxies to it

---

## Docker deployment

### Overview

The app runs as a single Docker container. The host uses nginx as reverse proxy; nginx fronts multiple services and forwards requests to this container by path or subdomain.

### Port choice

Use **18765** for the app inside the container. It’s high enough to avoid typical ports (80, 443, 3000, 5000, 8000, 8080, etc.) and unlikely to clash with other services.

### Container layout

- **Exposed port:** `18765`
- **Base image:** `python:3.11-slim` (or `python:3.12-slim`)
- **Includes:** ffmpeg (for video creation)
- **Volumes:** Config (YouTube OAuth secrets), temp directory (downloads/videos)
- **Env:** `SECRET_KEY`, `BASE_URL`, etc.

### nginx reverse proxy (host)

Example nginx config for a subdomain or path:

```nginx
# Subdomain: archive-to-yt.example.com
server {
    listen 443 ssl;
    server_name archive-to-yt.example.com;

    location / {
        proxy_pass http://127.0.0.1:18765;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 86400;   # Long for WebSocket / long uploads
    }
}
```

Or by path on an existing server:

```nginx
location /archive-to-yt/ {
    proxy_pass http://127.0.0.1:18765/;
    # ... same headers as above
}
```

### Docker Compose (for dev or simple deploy)

```yaml
services:
  archive-to-yt:
    build: .
    ports:
      - "18765:18765"
    environment:
      - SECRET_KEY=${SECRET_KEY}
      - BASE_URL=${BASE_URL:-http://localhost:18765}
    volumes:
      - ./config:/app/config:ro
      - archive-to-yt-temp:/app/temp
volumes:
  archive-to-yt-temp:
```

### Project structure (Docker additions)

```
archive-to-yt/
├── Dockerfile
├── docker-compose.yml
├── .dockerignore
└── ...
```

---

## Architecture

### High-level

```
┌─────────────────┐     HTTP/WebSocket      ┌─────────────────────┐
│   Web frontend  │ ◄─────────────────────► │   Backend (FastAPI) │
│   (HTML/JS)     │                         │   + existing src/   │
└─────────────────┘                         └──────────┬──────────┘
                                                       │
                                                       ▼
                                              ┌─────────────────────┐
                                              │  Per-session state  │
                                              │  - YouTube tokens   │
                                              │  - Job progress     │
                                              └─────────────────────┘
```

### Tech stack

| Component   | Choice       | Rationale                                             |
|------------|--------------|--------------------------------------------------------|
| Backend    | **FastAPI**  | Async, OpenAPI docs, WebSockets, type hints, modern   |
| Frontend   | **Vanilla JS + HTML/CSS** | Simple, no build step, easy to host                  |
| Auth       | **OAuth 2.0 web flow** | Required for hosted app (no local browser)           |
| Sessions   | **Encrypted cookies**  | Per-user YouTube tokens, no login system needed      |
| Long tasks | **Background jobs + WebSockets** | Progress updates during download/encode/upload     |

---

## OAuth flow (YouTube)

CLI uses `InstalledAppFlow.run_local_server()` (desktop). For web:

1. **Redirect flow**
   - User clicks “Sign in with YouTube”
   - Backend redirects to Google OAuth consent URL
   - User approves
   - Google redirects to our callback URL with `?code=...`
   - Backend exchanges `code` for tokens and stores them in session

2. **Token storage**
   - Tokens stored server-side keyed by session ID
   - Session ID in encrypted cookie
   - Option: in-memory (simplest) or Redis/DB if scaling

3. **Google Cloud setup**
   - OAuth client type: **Web application** (not Desktop)
   - Authorized redirect URIs: `https://your-domain.com/api/auth/youtube/callback` (and `http://localhost:...` for dev)

---

## API design

### Auth

| Method | Endpoint                      | Description                          |
|--------|-------------------------------|--------------------------------------|
| GET    | `/api/auth/youtube/url`       | Get YouTube OAuth URL to redirect to |
| GET    | `/api/auth/youtube/callback`  | OAuth callback (handles `?code`)     |
| GET    | `/api/auth/status`            | Whether user has valid YouTube auth  |
| POST   | `/api/auth/logout`            | Clear session / logout               |

### Workflow

| Method | Endpoint              | Description                                  |
|--------|------------------------|----------------------------------------------|
| POST   | `/api/preview`         | Submit URL → return preview (no downloads)   |
| POST   | `/api/process`         | Start process (download, create videos, upload) |
| GET    | `/api/job/{job_id}`    | Job status + progress                        |
| WS     | `/api/job/{job_id}/progress` | WebSocket for live progress              |
| POST   | `/api/job/{job_id}/publish`  | Make videos + playlist public            |
| GET    | `/api/job/{job_id}/playlist` | Get private playlist URL for review      |

### Preview response (example)

```json
{
  "metadata": {
    "title": "...",
    "performer": "...",
    "venue": "...",
    "date": "...",
    "url": "https://archive.org/details/...",
    "identifier": "..."
  },
  "playlist": {
    "title": "...",
    "description": "...",
    "track_count": 15
  },
  "tracks": [
    {
      "number": 1,
      "name": "Track Name",
      "video_title": "...",
      "duration_seconds": 245.5,
      "description_preview": "..."
    }
  ],
  "total_duration_seconds": 3600
}
```

---

## Frontend flow (mirrors CLI)

1. **Landing**
   - Input: archive.org URL
   - Button: “Sign in with YouTube” (if not signed in)
   - Button: “Preview”

2. **Preview**
   - Show collection metadata
   - Show playlist info
   - Table: track name, video title, duration
   - Total duration
   - Button: “Proceed” / “Cancel”

3. **Processing**
   - Progress: download / create / upload per track
   - WebSocket for live updates
   - Link to private playlist when done

4. **Review**
   - Link to private playlist
   - Instructions to review on YouTube
   - Button: “Make public” / “Cancel”

5. **Complete**
   - Link to public playlist

---

## Project structure (proposed)

```
archive-to-yt/
├── Dockerfile              # Single image (Python + ffmpeg)
├── docker-compose.yml      # Dev/simple deploy
├── .dockerignore
├── src/                    # Existing (unchanged core logic)
│   ├── archive_scraper.py
│   ├── audio_downloader.py
│   ├── metadata_formatter.py
│   ├── video_creator.py
│   ├── youtube_uploader.py  # Will need web-OAuth variant
│   └── main.py              # CLI entry (unchanged)
├── backend/                 # New: FastAPI app
│   ├── __init__.py
│   ├── main.py              # FastAPI app entry
│   ├── api/
│   │   ├── auth.py
│   │   ├── preview.py
│   │   ├── process.py
│   │   └── jobs.py
│   ├── services/
│   │   └── youtube_web_auth.py  # OAuth web flow
│   └── models/
├── frontend/                # New: static files
│   ├── index.html
│   ├── static/
│   │   ├── css/
│   │   └── js/
│   └── ...
├── config/
│   ├── client_secrets.json  # Same as CLI (Web client type)
│   └── ...
├── upload.py                # CLI (unchanged)
└── run_web.py               # Start FastAPI server
```

---

## Implementation phases

### Phase 0: Docker (early)

- [ ] `Dockerfile` – Python base, ffmpeg, app code
- [ ] `docker-compose.yml` – Dev/simple deploy
- [ ] `.dockerignore` – Exclude venv, temp, etc.
- [ ] App listens on `PORT` (default `18765`)

### Phase 1: Backend skeleton

- [ ] FastAPI app with `/health`
- [ ] Static file serving for frontend
- [ ] Session middleware (encrypted cookies)
- [ ] CORS for local dev

### Phase 2: YouTube OAuth (web flow)

- [ ] `youtube_web_auth.py` – authorization URL, token exchange
- [ ] `/api/auth/youtube/url` and `/api/auth/youtube/callback`
- [ ] Store tokens in session
- [ ] `YouTubeUploader` that accepts credentials (not file path)

### Phase 3: Preview API

- [ ] Reuse `ArchiveScraper`, `MetadataFormatter`, `AudioDownloader.get_audio_duration_from_url`
- [ ] `POST /api/preview` with `{"url": "..."}`

### Phase 4: Process API (background jobs)

- [ ] Job queue (in-memory or simple DB)
- [ ] `POST /api/process` → create job, return `job_id`
- [ ] Background worker: run existing `ArchiveToYouTube` logic
- [ ] WebSocket or polling for progress

### Phase 5: Frontend

- [ ] Landing page: URL input + Sign in
- [ ] Preview page: table, metadata, “Proceed”
- [ ] Processing page: progress UI
- [ ] Review page: link, “Make public”
- [ ] Complete page: public playlist link

### Phase 6: Publish flow

- [ ] `POST /api/job/{id}/publish`
- [ ] Reuse `make_videos_public`, `update_playlist_privacy`

---

## Security considerations

- **HTTPS** – Required for production (OAuth, cookies)
- **Session secrets** – Strong random secret for signing
- **Token storage** – Server-side only; never expose to client
- **Rate limiting** – Prevent abuse (optional, later)
- **Temp files** – Clean up per job; isolate by job/session

---

## Configuration

Environment variables (or `.env`):

- `SECRET_KEY` – Session signing (required)
- `YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET` – Or use `client_secrets.json` with Web client
- `BASE_URL` – For OAuth redirect (e.g. `https://archive-to-yt.example.com`); nginx forwards here
- `TEMP_DIR` – Where to store downloads/videos (default: `/app/temp` in container)
- `PORT` – Internal port (default: `18765`)

**Docker:** Mount `config/` containing `client_secrets.json` (Web application type) into the container.

**Behind nginx:** The app must trust `X-Forwarded-Proto` and `X-Forwarded-Host` for generating OAuth redirect URLs and absolute links (nginx terminates SSL).

---

## Open questions

1. **User identification** – Session-only vs optional login (email/password)?
2. **Concurrent jobs** – One active job per user, or allow multiple?
3. **Job history** – Persist job metadata for “my uploads” list, or ephemeral?
4. **Styling** – Minimal CSS vs a small framework (e.g. Pico CSS)?

---

## Next steps

1. Review this plan and adjust as needed.
2. Implement Phase 1 (backend skeleton).
3. Implement Phase 2 (YouTube OAuth web flow).
4. Continue through phases.
