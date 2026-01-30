# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.4.0-beta] - 2026-01-30

### Added
- Interactive publish workflow: after upload, script offers to make videos and playlist public
- `update_video_privacy()` method to change video privacy status (private/unlisted/public)
- `update_playlist_privacy()` method to change playlist privacy status
- `make_videos_public()` method to batch update multiple videos to public
- Automatic check for existing YouTube videos before uploading (prevents duplicates)
- `find_existing_videos()` method to search YouTube for videos with matching archive.org URL
- Script now skips download/video creation/upload if video already exists on YouTube

### Changed
- Videos and playlists are created as private by default
- After successful upload, script prompts user to review playlist and optionally make it public
- Improved workflow: check for existing videos before processing tracks

### Fixed
- Fixed YouTube playlist creation permissions by adding `youtube` scope in addition to `youtube.upload`
- Fixed performer vs recorder in descriptions (now correctly shows "performed by [Band]" and "Recorded by [Recorder]")
- Fixed venue cleaning to remove band name prefixes like [Romp]
- Fixed background image validation false alarm (images no longer validated as audio files)

## [0.3.1-beta] - 2026-01-30

### Added
- Video file resume capability: existing videos are detected and reused instead of recreating
- `find_existing_videos()` method to check for existing video files before starting
- Video files are preserved until successful YouTube upload (not deleted after creation)

### Changed
- Video creation now accepts `skip_if_exists` parameter (default: True)
- Video files are only deleted after successful YouTube upload, not after creation
- Resume check now shows both audio and video files that will be reused

### Fixed
- Video files are preserved if YouTube upload fails, allowing resume without re-encoding
- Improved resume capability to avoid redundant ffmpeg video creation work

## [0.3.0-beta] - 2026-01-29

### Added
- Resume capability: automatically detects and reuses existing audio file downloads
- Identifier-based file naming: files are named with archive.org identifier for unique identification
- Deferred cleanup: audio files are only deleted after successful YouTube upload (not after video creation)
- Progress preservation: if process is interrupted, audio files are preserved for resume
- `find_existing_files()` method to check for existing downloads before starting

### Changed
- Audio files are now named with format: `{identifier}_track_{number}_{filename}`
- Background images are now named with format: `{identifier}_background_image.jpg`
- Video files are now named with format: `{identifier}_video_{number}.mp4`
- Cleanup strategy: audio files only deleted after successful upload, not after video creation
- Download method now accepts `skip_if_exists` parameter (default: True)

### Fixed
- Audio files are preserved if video creation or upload fails, allowing resume
- Interrupted processes can now be resumed without re-downloading all files

## [0.2.0-beta] - 2026-01-29

### Changed
- **BREAKING**: Refactored `ArchiveScraper` to use Archive.org Metadata API instead of HTML scraping
  - Replaced BeautifulSoup-based HTML parsing with direct API calls
  - More reliable file detection and metadata extraction
  - Improved performance with single API call vs. HTML parsing

### Removed
- Removed `beautifulsoup4` dependency (no longer needed)
- Removed `lxml` dependency (was only used for BeautifulSoup)

### Fixed
- Fixed issue where audio files were not being detected on some archive.org pages
- Improved track-to-file matching with better filename pattern recognition

## [0.1.0-beta] - 2026-01-29

### Added
- Initial beta release
- Archive.org metadata extraction
- Audio file download functionality
- Video creation using ffmpeg with high-quality settings
- YouTube API integration with OAuth2 authentication
- Automatic playlist creation
- Metadata formatting for YouTube descriptions
- Comprehensive logging throughout
- Automatic cleanup of temporary files
- Full documentation (README.md, ARCHITECTURE.md)

[Unreleased]: https://github.com/151henry151/archive-to-yt/compare/v0.3.1-beta...HEAD
[0.3.1-beta]: https://github.com/151henry151/archive-to-yt/compare/v0.3.0-beta...v0.3.1-beta
[0.3.0-beta]: https://github.com/151henry151/archive-to-yt/compare/v0.2.0-beta...v0.3.0-beta
[0.2.0-beta]: https://github.com/151henry151/archive-to-yt/compare/v0.1.0-beta...v0.2.0-beta
[0.1.0-beta]: https://github.com/151henry151/archive-to-yt/tag/v0.1.0-beta

