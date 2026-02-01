# Web UI Setup

## YouTube OAuth (Web Client)

The web UI uses a **Web application** OAuth client (not the Desktop client used by the CLI). You need to create one in Google Cloud Console:

1. Go to [Google Cloud Console](https://console.cloud.google.com/) → APIs & Services → Credentials
2. Create OAuth 2.0 Client ID (or edit existing)
3. **Application type:** Web application
4. **Authorized redirect URIs:** Add:
   - `http://localhost:18765/api/auth/youtube/callback` (local dev)
   - `https://your-domain.com/api/auth/youtube/callback` (production)
5. Download the JSON and save as `config/client_secrets.json` (replace or keep both Desktop + Web entries in the same file if your JSON supports multiple clients)

> **Note:** The same `client_secrets.json` can contain both "installed" (for CLI) and "web" (for web UI) client configs. The Flow will use the appropriate one based on `redirect_uri`.

## Running

### Option 1: Direct (no Docker)

```bash
pip install -r requirements.txt
export SECRET_KEY="your-secret-key-for-sessions"
python run_web.py
```

Open http://localhost:18765

### Option 2: Docker

```bash
# Create config/client_secrets.json first (see above)
export SECRET_KEY="your-secret-key"
docker compose up --build
```

Open http://localhost:18765

### Option 3: Docker (production with nginx)

1. Build: `docker build -t archive-to-yt .`
2. Run with volume: `docker run -p 18765:18765 -v $(pwd)/config:/app/config:ro -e SECRET_KEY=xxx archive-to-yt`
3. Configure nginx to proxy to `http://127.0.0.1:18765`
4. Set `BASE_URL` to your public URL (e.g. `https://archive-to-yt.example.com`)

## Environment Variables

| Variable     | Default              | Description                    |
|-------------|----------------------|--------------------------------|
| PORT        | 18765                | Port to listen on              |
| HOST        | 0.0.0.0              | Host to bind to                |
| SECRET_KEY  | (required in prod)   | Session signing key            |
| BASE_URL    | (optional)           | Public URL for OAuth redirects |
