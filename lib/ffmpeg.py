import json
import subprocess
from datetime import datetime
from typing import Optional

FFMPEG_TAGS = ["com.apple.quicktime.creationdate", "creation_time", "date"]


def get_ffmpeg_date(path: str) -> Optional[datetime]:
    """
    Extracts the creation date of a video using ffprobe.

    Parameters
    ----------
    path : str
        Path to the video file.

    Returns
    -------
    Optional[datetime]
        Parsed datetime object if found, otherwise None.
    """
    try:
        # ffprobe command to get metadata in JSON
        cmd = [
            "ffprobe",
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            path,
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)

        # Possible metadata keys that may contain creation date
        date_keys = FFMPEG_TAGS
        # Search in format tags
        tags = data.get("format", {}).get("tags", {})
        for key in date_keys:
            if key in tags:
                return _parse_date(tags[key])

        # Search in stream tags (fallback)
        for stream in data.get("streams", []):
            stags = stream.get("tags", {})
            for key in date_keys:
                if key in stags:
                    return _parse_date(stags[key])

        return None

    except Exception as exc:
        print(f"Error reading metadata: {exc}")
        return None


def _parse_date(value: str) -> Optional[datetime]:
    """
    Try multiple date formats because ffprobe outputs vary.
    """
    formats = [
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue

    return None


# def get_ffmpeg_date(full_path: Path) -> Optional[date]:
#     """Extract date taken from media metadata using ffmpeg."""
#     try:
#         probe = ffmpeg.probe(full_path)
#     except Exception as _:
#         return None

#     # Extract relevant tags from ffmpeg metadata
#     format_tags = probe.get("format", {}).get("tags", {})
#     print(format_tags)
#     date_ffmpeg = None

#     # Check known ffmpeg date tags
#     for tag in FFMPEG_TAGS:
#         dt = format_tags.get(tag)
#         if dt:
#             dt = datetime.fromisoformat(dt.replace("Z", "+00:00"))
#             dt = get_utc_time(dt)
#             date_ffmpeg = get_min(date_ffmpeg, dt)
#     return date_ffmpeg
