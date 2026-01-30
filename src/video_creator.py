"""
Video creator using ffmpeg.

Combines audio tracks with static background images to create videos.
"""

import json
import logging
import subprocess
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)


class VideoCreator:
    """Creates videos from audio and images using ffmpeg."""

    def __init__(self, temp_dir: str = "temp"):
        """
        Initialize video creator.

        Args:
            temp_dir: Directory to store created video files
        """
        self.temp_dir = Path(temp_dir)
        self.temp_dir.mkdir(exist_ok=True)
        self._check_ffmpeg()
        logger.info(f"Video creator initialized with temp directory: {self.temp_dir}")

    def _check_ffmpeg(self) -> None:
        """Check if ffmpeg is available."""
        try:
            result = subprocess.run(
                ['ffmpeg', '-version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode != 0:
                raise RuntimeError("ffmpeg is not working properly")
            logger.info("ffmpeg is available")
        except (FileNotFoundError, subprocess.TimeoutExpired) as e:
            logger.error("ffmpeg is not installed or not in PATH")
            raise RuntimeError(
                "ffmpeg is required but not found. "
                "Please install ffmpeg: https://ffmpeg.org/download.html"
            ) from e

    def _validate_video_file(self, video_path: Path, expected_duration: Optional[float] = None) -> bool:
        """
        Validate that a video file is complete and valid.
        
        Args:
            video_path: Path to video file to validate
            expected_duration: Optional expected duration in seconds (for comparison)
            
        Returns:
            True if video is valid, False otherwise
        """
        if not video_path.exists():
            return False
        
        # Check file size - must be at least 1KB (very small files are likely corrupted)
        file_size = video_path.stat().st_size
        if file_size < 1024:  # Less than 1KB is suspicious
            logger.warning(f"Video file is suspiciously small ({file_size} bytes), likely corrupted")
            return False
        
        # Validate video file using ffprobe
        try:
            cmd = [
                'ffprobe',
                '-v', 'error',
                '-show_entries', 'format=duration:stream=codec_type,duration',
                '-of', 'json',
                str(video_path)
            ]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                logger.warning(f"ffprobe validation failed for {video_path.name}: {result.stderr}")
                return False
            
            # Check if we got valid JSON output
            try:
                probe_data = json.loads(result.stdout)
                format_info = probe_data.get('format', {})
                
                # Check if format duration exists and is valid
                duration_str = format_info.get('duration', '0')
                if duration_str:
                    duration = float(duration_str)
                    if duration <= 0:
                        logger.warning(f"Video has invalid duration ({duration} seconds)")
                        return False
                    
                    # If expected duration provided, check if it matches (within 5 seconds tolerance)
                    if expected_duration and abs(duration - expected_duration) > 5:
                        logger.warning(
                            f"Video duration ({duration:.2f}s) doesn't match expected "
                            f"({expected_duration:.2f}s), likely incomplete"
                        )
                        return False
                
                # Check if video and audio streams exist
                streams = probe_data.get('streams', [])
                has_video = any(s.get('codec_type') == 'video' for s in streams)
                has_audio = any(s.get('codec_type') == 'audio' for s in streams)
                
                if not has_video:
                    logger.warning(f"Video file has no video stream")
                    return False
                if not has_audio:
                    logger.warning(f"Video file has no audio stream")
                    return False
                
                logger.debug(f"Video file validated successfully: duration={duration:.2f}s, size={file_size / (1024*1024):.2f}MB")
                return True
                
            except (json.JSONDecodeError, ValueError, KeyError) as e:
                logger.warning(f"Failed to parse ffprobe output for {video_path.name}: {e}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.warning(f"ffprobe validation timed out for {video_path.name}")
            return False
        except Exception as e:
            logger.warning(f"Error validating video file {video_path.name}: {e}")
            return False

    def create_video(
        self,
        audio_path: Path,
        image_path: Path,
        output_path: Path,
        duration: Optional[float] = None,
        skip_if_exists: bool = True
    ) -> Path:
        """
        Create a video from audio and image.

        Args:
            audio_path: Path to audio file
            image_path: Path to background image
            output_path: Path to save output video
            duration: Optional duration override (if None, uses audio duration)
            skip_if_exists: If True, skip creation if video already exists and is valid (resume capability)

        Returns:
            Path to created video file
        """
        logger.info(f"Creating video from audio: {audio_path}")
        logger.info(f"Using background image: {image_path}")
        logger.info(f"Output video: {output_path}")

        # Get expected duration for validation
        if duration is None:
            duration = self._get_audio_duration(audio_path)
            logger.info(f"Audio duration: {duration:.2f} seconds")

        # Check if video already exists (resume capability)
        if skip_if_exists and output_path.exists():
            file_size = output_path.stat().st_size / (1024 * 1024)
            logger.info(f"Video file exists: {output_path} ({file_size:.2f} MB)")
            logger.info("Validating existing video file...")
            
            # Validate the existing video file
            if self._validate_video_file(output_path, duration):
                logger.info(f"Existing video is valid, skipping creation: {output_path}")
                return output_path
            else:
                logger.warning(f"Existing video file is corrupted or incomplete, will recreate: {output_path}")
                # Delete corrupted file
                try:
                    output_path.unlink()
                    logger.info(f"Deleted corrupted video file: {output_path}")
                except Exception as e:
                    logger.warning(f"Failed to delete corrupted video file: {e}")
                # Continue to create new video

        # Duration should already be set from validation check above
        # If we're here, we need to create the video

        # Build ffmpeg command
        # High quality settings:
        # - Video: H.264 codec, high quality preset, 1920x1080 resolution
        # - Audio: AAC codec, 192kbps bitrate (high quality within YouTube limits)
        # - Loop image for full duration
        cmd = [
            'ffmpeg',
            '-loop', '1',  # Loop the image
            '-i', str(image_path),  # Input image
            '-i', str(audio_path),  # Input audio
            '-c:v', 'libx264',  # Video codec
            '-preset', 'slow',  # High quality encoding (slower but better)
            '-crf', '18',  # High quality (lower = better, 18 is visually lossless)
            '-c:a', 'aac',  # Audio codec
            '-b:a', '192k',  # Audio bitrate (high quality, within YouTube limits)
            '-shortest',  # End when shortest input ends
            '-pix_fmt', 'yuv420p',  # Pixel format for compatibility
            '-vf', 'scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2',  # Scale and pad to 1080p
            '-y',  # Overwrite output file
            str(output_path)
        ]

        try:
            logger.info("Running ffmpeg to create video...")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=3600  # 1 hour timeout
            )

            if result.returncode != 0:
                logger.error(f"ffmpeg failed with return code {result.returncode}")
                logger.error(f"ffmpeg stderr: {result.stderr}")
                raise RuntimeError(f"Failed to create video: {result.stderr}")

            if not output_path.exists():
                raise RuntimeError("Video file was not created")

            # Validate the newly created video
            logger.info("Validating newly created video...")
            if not self._validate_video_file(output_path, duration):
                # Clean up invalid video
                if output_path.exists():
                    output_path.unlink()
                raise RuntimeError("Created video file failed validation - may be corrupted")

            file_size = output_path.stat().st_size / (1024 * 1024)
            logger.info(f"Successfully created and validated video: {output_path} ({file_size:.2f} MB)")

            return output_path

        except subprocess.TimeoutExpired:
            logger.error("ffmpeg timed out while creating video")
            raise RuntimeError("Video creation timed out")
        except Exception as e:
            logger.error(f"Error creating video: {e}")
            # Clean up partial output
            if output_path.exists():
                output_path.unlink()
            raise

    def _get_audio_duration(self, audio_path: Path) -> float:
        """
        Get duration of audio file using ffprobe.

        Args:
            audio_path: Path to audio file

        Returns:
            Duration in seconds
        """
        try:
            cmd = [
                'ffprobe',
                '-v', 'error',
                '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                str(audio_path)
            ]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                return float(result.stdout.strip())
            else:
                logger.warning(f"Could not get audio duration, using default")
                return 0.0
        except Exception as e:
            logger.warning(f"Error getting audio duration: {e}, using default")
            return 0.0

    def find_existing_videos(self, identifier: str) -> List[Path]:
        """
        Find existing video files for a given identifier (resume capability).
        
        Args:
            identifier: Archive.org identifier to search for
            
        Returns:
            List of existing video file paths
        """
        existing_videos = []
        pattern = f"{identifier}_video_*.mp4"
        for filepath in self.temp_dir.glob(pattern):
            if filepath.is_file():
                existing_videos.append(filepath)
        return sorted(existing_videos)

    def cleanup(self, filepath: Path) -> None:
        """
        Delete a video file.

        Args:
            filepath: Path to video file to delete
        """
        try:
            if filepath.exists():
                filepath.unlink()
                logger.debug(f"Cleaned up video file: {filepath}")
        except Exception as e:
            logger.warning(f"Failed to cleanup video file {filepath}: {e}")

