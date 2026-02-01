"""
Preview API - dry-run preview of what would be uploaded.
"""

import re
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

# Import from project root
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src.archive_scraper import ArchiveScraper
from src.audio_downloader import AudioDownloader
from src.metadata_formatter import MetadataFormatter

router = APIRouter()

ROOT = Path(__file__).resolve().parent.parent.parent
TEMP_DIR = ROOT / "temp"
TEMP_DIR.mkdir(exist_ok=True)


class PreviewRequest(BaseModel):
    url: str


@router.post("/preview")
def preview(request: PreviewRequest):
    """
    Generate preview of what would be uploaded for a given archive.org URL.
    No downloads except duration probing.
    """
    url = request.url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="URL is required")
    if "archive.org/details/" not in url:
        raise HTTPException(status_code=400, detail="Invalid archive.org URL")

    try:
        scraper = ArchiveScraper(url)
        metadata = scraper.extract_metadata()
        tracks = metadata.get("tracks", [])
        if not tracks:
            raise HTTPException(status_code=400, detail="No tracks found on archive.org page")

        track_audio = scraper.get_audio_file_urls()
        if not track_audio:
            raise HTTPException(status_code=400, detail="No audio files found for tracks")

        formatter = MetadataFormatter()
        audio_downloader = AudioDownloader(str(TEMP_DIR))

        playlist_title = formatter.format_playlist_title(metadata)
        playlist_description = formatter.format_playlist_description(metadata, tracks)

        preview_tracks = []
        total_duration = 0.0

        for i, track_info in enumerate(track_audio):
            track_num = track_info["number"]
            track_name = track_info["name"]
            audio_url = track_info["url"]

            # Sanitize track name (mirror main.py logic)
            track_info_clean = track_info.copy()
            track_name_clean = str(track_info.get("name", "Unknown Track")).strip()
            track_name_clean = re.sub(r"<[^>]+>", "", track_name_clean)
            track_name_clean = track_name_clean.replace("&gt;", ">").replace("&lt;", "<").replace("&amp;", "&")
            track_name_clean = re.sub(r"\s+", " ", track_name_clean).strip()
            if len(track_name_clean) > 100 or "\n" in track_name_clean:
                track_name_clean = track_name_clean.split("\n")[0].strip()
            if not track_name_clean:
                track_name_clean = f"Track {track_num}"
            track_info_clean["name"] = track_name_clean

            video_title = formatter.format_video_title(track_info_clean, metadata)
            if not video_title or not video_title.strip():
                video_title = f"Track {track_num} - {track_name_clean}"

            duration = audio_downloader.get_audio_duration_from_url(audio_url)
            if duration:
                total_duration += duration

            video_description = formatter.format_track_description(track_info_clean, metadata)
            description_preview = video_description[:300] + "..." if len(video_description) > 300 else video_description

            preview_tracks.append({
                "number": track_num,
                "name": track_name,
                "video_title": video_title,
                "duration_seconds": round(duration, 1) if duration else None,
                "description_preview": description_preview,
                "audio_filename": track_info.get("filename", "unknown"),
            })

        return {
            "metadata": {
                "title": metadata.get("title", "Unknown"),
                "performer": metadata.get("performer", "Unknown"),
                "venue": metadata.get("venue", "Unknown"),
                "date": metadata.get("date", "Unknown"),
                "url": metadata.get("url", url),
                "identifier": metadata.get("identifier", "unknown"),
            },
            "playlist": {
                "title": playlist_title,
                "description": playlist_description,
                "track_count": len(preview_tracks),
            },
            "tracks": preview_tracks,
            "total_duration_seconds": round(total_duration, 1),
        }

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
