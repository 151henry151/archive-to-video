"""
Process API - start and track upload jobs.
"""

import logging
import sys
import threading
import uuid
from pathlib import Path

from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel

# Add project root
ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from backend.api.auth import get_session_credentials
from src.main import ArchiveToYouTube

logger = logging.getLogger(__name__)

router = APIRouter()

# In-memory job store (use Redis/DB for multi-worker in production)
jobs: dict = {}


class ProcessRequest(BaseModel):
    url: str


def run_job(job_id: str, url: str, credentials):
    """Background task to run the upload workflow."""
    try:
        jobs[job_id]["status"] = "running"
        jobs[job_id]["progress"] = {"message": "Starting...", "current": 0, "total": 0}

        uploader = ArchiveToYouTube(
            temp_dir=str(ROOT / "temp"),
            credentials_path=str(ROOT / "config" / "client_secrets.json"),
            credentials=credentials,
        )

        def progress_cb(msg, current, total):
            jobs[job_id]["progress"] = {"message": msg, "current": current, "total": total}

        result = uploader.process_archive_url(
            url, interactive=False, progress_callback=progress_cb
        )

        if result:
            jobs[job_id]["status"] = "complete"
            jobs[job_id]["result"] = result
            jobs[job_id]["progress"] = {"message": "Complete!", "current": 1, "total": 1}
        else:
            jobs[job_id]["status"] = "failed"
            jobs[job_id]["error"] = "Process returned no result"
    except Exception as e:
        logger.exception(f"Job {job_id} failed")
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)


@router.post("/process")
def start_process(request: Request, body: ProcessRequest):
    """Start a new upload job. Returns job_id for tracking."""
    creds = get_session_credentials(request)
    if not creds:
        raise HTTPException(status_code=401, detail="Not authenticated with YouTube. Sign in first.")

    url = body.url.strip()
    if not url or "archive.org/details/" not in url:
        raise HTTPException(status_code=400, detail="Invalid archive.org URL")

    job_id = str(uuid.uuid4())[:8]
    jobs[job_id] = {
        "status": "pending",
        "url": url,
        "progress": {"message": "Queued...", "current": 0, "total": 0},
        "result": None,
        "error": None,
    }

    thread = threading.Thread(
        target=run_job,
        args=(job_id, url, creds),
    )
    thread.daemon = True
    thread.start()

    return {"job_id": job_id}


@router.get("/job/{job_id}")
def get_job_status(request: Request, job_id: str):
    """Get job status and result."""
    creds = get_session_credentials(request)
    if not creds:
        raise HTTPException(status_code=401, detail="Not authenticated")

    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = jobs[job_id]
    resp = {
        "job_id": job_id,
        "status": job["status"],
        "progress": job["progress"],
    }
    if job["status"] == "complete" and job.get("result"):
        resp["playlist_url"] = job["result"].get("playlist_url")
        resp["playlist_id"] = job["result"].get("playlist_id")
        resp["video_ids"] = job["result"].get("video_ids", [])
    if job["status"] == "failed" and job.get("error"):
        resp["error"] = job["error"]
    return resp


@router.post("/job/{job_id}/publish")
def publish_job(request: Request, job_id: str):
    """Make videos and playlist public."""
    creds = get_session_credentials(request)
    if not creds:
        raise HTTPException(status_code=401, detail="Not authenticated")

    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = jobs[job_id]
    if job["status"] != "complete":
        raise HTTPException(status_code=400, detail="Job not complete yet")

    result = job.get("result")
    if not result:
        raise HTTPException(status_code=400, detail="No result")

    playlist_id = result.get("playlist_id")
    video_ids = result.get("video_ids", [])
    if not playlist_id:
        raise HTTPException(status_code=400, detail="No playlist")

    try:
        uploader = ArchiveToYouTube(
            temp_dir=str(ROOT / "temp"),
            credentials_path=str(ROOT / "config" / "client_secrets.json"),
            credentials=creds,
        )
        success_count = uploader.youtube_uploader.make_videos_public(video_ids)
        playlist_updated = uploader.youtube_uploader.update_playlist_privacy(playlist_id, "public")
        playlist_url = result.get("playlist_url", f"https://www.youtube.com/playlist?list={playlist_id}")
        return {
            "ok": True,
            "videos_made_public": success_count,
            "playlist_updated": playlist_updated,
            "playlist_url": playlist_url,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
