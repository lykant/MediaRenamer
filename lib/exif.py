import os
import exifread
from typing import Optional
from pathlib import Path
from datetime import date, datetime, timezone

DT_FORMAT = "%Y:%m:%d %H:%M:%S"
EXIF_TAGS = ["Image DateTime", "EXIF DateTimeOriginal", "EXIF DateTimeDigitized"]


def get_min(value1: Optional[date], value2: Optional[date]) -> Optional[date]:
    """Return the minimum of two date values, handling None values."""
    min_value = min(value1, value2) if value1 and value2 else value1 or value2
    return min_value


def get_utc_time(_time: datetime) -> Optional[datetime]:
    """Convert a naive datetime to UTC timezone-aware datetime."""
    # If no time provided, return None
    if not _time:
        return None
    r_time = _time.replace(tzinfo=timezone.utc)
    return r_time


def get_os_date(full_path: Path) -> Optional[date]:
    """Return the earliest of creation or modification time as UTC date."""
    # Get file system timestamps
    c_date = datetime.fromtimestamp(os.path.getctime(full_path))
    c_date = get_utc_time(c_date)
    m_date = datetime.fromtimestamp(os.path.getmtime(full_path))
    m_date = get_utc_time(m_date)

    # OS date cannot be empty.
    date_taken = get_min(c_date, m_date)
    return date_taken


def get_date_taken(full_path: Path) -> Optional[date]:
    """
    Extract the earliest valid date value from EXIF metadata using exifread.
    Checked tags (in order of priority):
        - DateTimeOriginal
        - DateTimeDigitized
        - DateTime

    Returns the earliest UTC-normalized date found, or None.
    """
    date_taken: Optional[date] = None
    # Read EXIF data from the image file
    with open(full_path, "rb") as image:
        exif = exifread.process_file(image, details=False)

    # Check known EXIF date tags
    for tag in EXIF_TAGS:
        raw = exif.get(tag)
        if not raw:
            continue

        # Parse and normalize the date, then find the minimum with existing date_taken
        try:
            dt = datetime.strptime(str(raw), DT_FORMAT)
            dt = get_utc_time(dt)
            date_taken = get_min(date_taken, dt)
        except Exception:
            ...
    return date_taken


if __name__ == "__main__":
    from pillow_heif import register_heif_opener
