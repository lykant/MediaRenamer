"""
Media Renamer
-------------

A tool for organizing large photo and video libraries by generating consistent,
chronological filenames based on the most reliable "date taken" metadata.
It extracts timestamps from EXIF, FFmpeg headers, and OS data, then builds a
unified index to determine correct ordering.

The system detects naming conflicts, groups simultaneous captures, applies
deterministic suffix rules, and performs safe, logged renaming. Processing
runs folder by folder for reproducible results even with incomplete metadata.

Core features:
- Extracts dates from EXIF, FFmpeg, and OS metadata
- Produces stable chronological filenames
- Resolves naming conflicts and mutual groups
- Builds a global metadata index
- Performs safe renaming with structured logging

Designed for clarity, reproducibility, and robustness in real-world libraries.
"""

import os
import ffmpeg
import exifread
import subprocess
import pandas as pd
import lib.logger as logger
from typing import Optional
from dataclasses import dataclass
from pathlib import Path
from datetime import date, datetime, timezone
from itertools import product
from pillow_heif import register_heif_opener


# Constants
APP_NAME = Path(__file__).stem
NAME_FORMAT = "%Y%m%d-%H%M%S"
DT_FORMAT = "%Y:%m:%d %H:%M:%S"
ISO_FORMAT = "%Y-%m-%d %H:%M:%S"

SLASH = "\\"
DIYEZ = "#"
EQUAL = "="
HYPHEN = "-"
BLANK = ""

NAME_LENGTH = 15
LINE_LENGTH = 60
YES = True
NO = False
MSG_PREFIX = "{no}- {name} >> "

FILE_EXTENSIONS = ["jpg", "heic", "mov", "mp4", "mpg", "gif", "m4a"]
EXIF_TAGS = ["Image DateTime", "EXIF DateTimeOriginal", "EXIF DateTimeDigitized"]
FFMPEG_TAGS = ["com.apple.quicktime.creationdate", "creation_time"]


@dataclass
class Metadata:
    """
    Holds all metadata used during the media renaming process.

    Stores original file info, extracted date values, generated names,
    mutual group ordering, and conflict flags. The renaming pipeline
    updates this object step by step to produce deterministic and
    consistent output filenames.
    """

    no: int = 0
    folder: Path | None = None
    initial_name: str | None = None
    actual_name: str | None = None
    actual_full_name: str | None = None
    actual_full_path: Path | None = None
    date_taken: date | None = None
    new_name: str | None = None
    new_full_name: str | None = None
    new_full_path: Path | None = None
    ext: str | None = None
    is_mutual: bool = NO
    mutual_order: int = 0
    mutual_suffix: str = DIYEZ
    has_conflict: bool = NO
    conflict_suffix: str = DIYEZ


def set_metadata(
    meta: Metadata,
    folder: Path | None = None,
    initial_name: str | None = None,
    actual_name: str | None = None,
    date_taken: date | None = None,
    new_name: str | None = None,
    ext: str | None = None,
    is_mutual: bool | None = None,
    mutual_order: int = 0,
    mutual_suffix: str = DIYEZ,
    has_conflict: bool | None = None,
    conflict_suffix: str = DIYEZ,
    no: int = 0,
):
    """
    Update Metadata fields selectively based on provided arguments.

    This function acts as a controlled mutator:
    - Only updates fields when a new value is provided.
    - Rebuilds full names and paths after updates.
    - Handles mutual-group suffixes and conflict suffixes.
    """

    # Update basic fields only when provided
    meta.no = no or meta.no
    meta.folder = folder or meta.folder
    meta.initial_name = initial_name or meta.initial_name
    meta.actual_name = actual_name or meta.actual_name
    meta.date_taken = date_taken or meta.date_taken
    meta.new_name = new_name or meta.new_name
    meta.ext = ext or meta.ext
    meta.mutual_suffix = mutual_suffix if mutual_suffix != DIYEZ else meta.mutual_suffix
    meta.conflict_suffix = (
        conflict_suffix if conflict_suffix != DIYEZ else meta.conflict_suffix
    )

    # Mutual group flags
    if is_mutual is not None:
        meta.is_mutual = is_mutual
        meta.mutual_order = mutual_order if meta.is_mutual else 0
        meta.mutual_suffix = f"{HYPHEN}{mutual_order:02d}" if meta.is_mutual else BLANK

    # Conflict flags
    if has_conflict is not None:
        meta.has_conflict = has_conflict
        meta.conflict_suffix = f"{DIYEZ}{meta.no:05d}" if meta.has_conflict else BLANK

    # Rebuild full names and paths
    set_actual_name(meta)
    set_new_name(meta)


def set_new_name(meta: Metadata):
    """
    Build the new file name and full path using:
    - date_taken (preferred)
    - new_name (fallback)
    - mutual suffix if part of a mutual group
    - conflict suffix if there is a conflict
    """

    # If no date and no new name, nothing to build
    if not meta.date_taken and not meta.new_name:
        return

    # Prefer EXIF/OS date; fallback to manually assigned new_name
    meta.new_name = date_to_str(meta.date_taken) or meta.new_name

    # Append mutual and conflict suffixes if applicable
    suffix = meta.mutual_suffix if meta.mutual_suffix != DIYEZ else BLANK
    suffix += meta.conflict_suffix if meta.conflict_suffix != DIYEZ else BLANK
    meta.new_name = f"{meta.new_name}{suffix}"

    # Build full new name and path
    meta.new_full_name = concat_full_name(meta.new_name, meta.ext)
    meta.new_full_path = concat_full_path(meta.folder, meta.new_full_name)


def set_actual_name(meta: Metadata):
    """
    Build the actual_full_name and actual_full_path fields
    based on the current actual_name and extension.
    """
    # If no actual name, nothing to build
    if not meta.actual_name:
        return

    # Build full file name and full path for the actual/original file
    meta.actual_full_name = concat_full_name(meta.actual_name, meta.ext)
    meta.actual_full_path = concat_full_path(meta.folder, meta.actual_full_name)


def concat_full_name(file_name: str, ext: str | None = None) -> str:
    """Return 'file_name.ext' if extension exists, otherwise return file_name."""
    # Build full file name
    full_name = f"{file_name}.{ext}" if ext else file_name
    return full_name


def concat_full_path(
    folder: Path | None,
    file_name: str,
    ext: str | None = None,
) -> Path:
    """Return full file path by combining folder and full file name."""
    # Build full file path
    full_name = concat_full_name(file_name, ext)
    full_path = Path(folder / full_name if folder else full_name)
    return full_path


def trim_string(full_string: str, char: str) -> str:
    """Return substring before the last occurrence of char."""
    idx = full_string.rfind(char)
    trimmed_string = full_string[:idx] if idx != -1 else full_string
    return trimmed_string


def date_to_str(_date: date | None) -> Optional[str]:
    """Convert date object to formatted string, or return None."""
    # If no date object, return None
    date_taken = _date.strftime(NAME_FORMAT) if _date else None
    return date_taken


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


def get_ffmpeg_date(full_path: Path) -> Optional[date]:
    """Extract date taken from media metadata using ffmpeg."""
    try:
        probe = ffmpeg.probe(full_path)
    except Exception as _:
        return None

    # Extract relevant tags from ffmpeg metadata
    format_tags = probe.get("format", {}).get("tags", {})
    date_ffmpeg = None

    # Check known ffmpeg date tags
    for tag in FFMPEG_TAGS:
        dt = format_tags.get(tag)
        if dt:
            dt = datetime.fromisoformat(dt.replace("Z", "+00:00"))
            dt = get_utc_time(dt)
            date_ffmpeg = get_min(date_ffmpeg, dt)
    return date_ffmpeg


def find_file_date(meta: Metadata) -> Optional[date]:
    """Determine the date taken for a file using EXIF, FFmpeg, and OS timestamps."""
    full_path = meta.actual_full_path
    ext = meta.ext
    date_taken = None

    # Try EXIF or FFmpeg depending on file type
    if ext in ["jpg", "heic"]:
        date_taken = get_date_taken(full_path)  # type: ignore
    elif ext in ["mov", "mp4", "mpg", "gif"]:
        date_taken = get_ffmpeg_date(full_path)  # type: ignore

    # Always fallback to OS timestamps
    date_os = get_os_date(full_path)  # type: ignore
    date_taken = get_min(date_taken, date_os)
    return date_taken


def os_rename(meta: Metadata):
    """Perform the actual filesystem rename operation."""
    os.rename(meta.actual_full_path, meta.new_full_path)  # type: ignore


def rename_all_files(only_conflicts: bool = NO):
    """Rename a file on the filesystem, optionally only if it has conflicts."""
    global list_metadata

    # Iterate over all metadata items and attempt to rename files, logging outcomes
    for meta in list_metadata:
        # If only processing conflicts, skip files that do not have a conflict
        # Otherwise skip the ones that have a conflict, since they will be processed in the next run
        if only_conflicts and not meta.has_conflict:
            continue

        # Safety check
        if not meta.new_full_path:
            raise Exception(
                MSG_PREFIX.format(no=meta.no, name=meta.actual_full_name)
                + "Error: File path cannot be none!"
            )

        # Check if the new name is the same as the actual name to avoid unnecessary renaming
        same_name = meta.new_full_name == meta.actual_full_name
        if same_name:
            log.info(
                MSG_PREFIX.format(no=meta.no, name=meta.actual_full_name)
                + "File names are identical"
            )
        else:
            # Attempt to rename the file and log the outcome
            try:
                os_rename(meta)
            except Exception as _:
                log.error(
                    MSG_PREFIX.format(no=meta.no, name=meta.actual_full_name)
                    + f"{meta.new_full_name} Error: Failed to rename file"
                )
                continue

            # Update metadata after rename
            log.info(
                MSG_PREFIX.format(no=meta.no, name=meta.actual_full_name)
                + f"Renamed to {meta.new_full_name}"
            )
            set_metadata(meta, actual_name=meta.new_name)


def search_mutual_names():
    """Mark files with the same date_taken as mutual."""
    global list_metadata

    # Collect all unique dates from the global media list
    unique_dates = list(dict.fromkeys([meta.date_taken for meta in list_metadata]))

    # Iterate over each unique date and file extension combination
    for _date, ext in product(unique_dates, FILE_EXTENSIONS):
        # Filter files that have the same date_taken and extension
        list_mutual = [
            item
            for item in list_metadata
            if item.date_taken == _date and item.ext == ext
        ]

        # If only one file exists for that date and extension, nothing to mark as mutual
        if len(list_mutual) <= 1:
            continue

        # Mark all files with the same date and extension as mutual
        i = 0
        for meta in list_mutual:
            i += 1
            set_metadata(
                meta,
                is_mutual=YES,
                mutual_order=i,
            )


def conflict_exists() -> bool:
    """Check if any items in the global metadata list have a conflict."""
    # Check if there is at least one conflicting file
    has_conflict = any(meta.has_conflict for meta in list_metadata)
    return has_conflict


def reset_conflicts():
    """Reset conflict flags and suffixes for all files in the global metadata list."""
    global list_metadata

    # Iterate over all metadata items and reset conflict flags and suffixes
    for meta in [m for m in list_metadata if m.has_conflict]:
        trimmed_name = trim_string(meta.new_name, DIYEZ)  # type: ignore
        set_metadata(meta, conflict_suffix=BLANK, new_name=trimmed_name)


def mark_conflicts():
    """Identify and mark files that have naming conflicts with other files."""
    global list_metadata

    # Iterate over each file and check for naming conflicts with other files
    for meta1 in list_metadata:
        # A conflict occurs when another file has the same new_full_name but
        # a different original file (different 'no')
        for meta2 in list_metadata:
            if meta2.actual_full_name == meta1.new_full_name and meta2.no != meta1.no:
                # Mark the file as having a conflict if a matching name is found
                set_metadata(meta1, has_conflict=YES)
                break  # No need to check further once a conflict is found


def print_conflict_header():
    """Print a header for the conflict processing phase."""
    log.info(EQUAL * LINE_LENGTH)
    # Centered header for conflict processing
    log.info(str.center("CONFLICTS RUNNING", LINE_LENGTH, " "))
    log.info(HYPHEN * LINE_LENGTH)


def print_processing_header(meta: Metadata):
    """Print a header for the current file extension being processed."""
    global dict_file_counts

    if meta.no > 1:
        return

    # Get the number of files being processed for the current extension
    file_number = dict_file_counts.get(meta.ext, 0)  # type: ignore
    if file_number == 0:
        return

    # Visual separator for processing phase
    log.info(str.center(f" {meta.ext.upper()} ", LINE_LENGTH, HYPHEN))  # type: ignore
    log.info(f"{file_number} files being processed... ")
    log.info(HYPHEN * LINE_LENGTH)


def find_file_counts(only_conflicts: bool = NO):
    """Return the global dictionary of file counts per extension."""
    global list_metadata, dict_file_counts

    # Count files per extension
    for ext in FILE_EXTENSIONS:
        if only_conflicts:
            count = sum(
                1 for item in list_metadata if item.ext == ext and item.has_conflict
            )
        else:
            count = sum(1 for item in list_metadata if item.ext == ext)
        dict_file_counts[ext] = count


def find_all_file_dates():
    """Extract date_taken for each file in the global metadata list."""
    global list_metadata

    # If no files to process, return early
    if len(list_metadata) == 0:
        return

    # Process each file for metadata extraction
    for meta in list_metadata:
        date_taken = None

        # Print header for the current file extension when processing the first file of that type
        print_processing_header(meta)

        # Log processing info for the current file
        log.info(
            MSG_PREFIX.format(no=meta.no, name=meta.actual_full_name) + "Processing..."
        )

        # Extract the date taken using the defined logic (EXIF/FFmpeg/OS)
        date_taken = find_file_date(meta)

        # Update metadata with extracted date
        set_metadata(meta, date_taken=date_taken)

    list_metadata = sorted(list_metadata, key=lambda x: (x.new_full_name, x.no))  # type: ignore
    log.info(HYPHEN * LINE_LENGTH)


def process_files():
    """Process files for metadata extraction and renaming, optionally only handling conflicts."""
    global list_metadata

    # Run the full processing pipeline for all files,
    # then optionally run only conflict processing if requested
    list_conflict_status = [NO, YES]
    for only_conflicts in list_conflict_status:
        # Count files per extension
        find_file_counts(only_conflicts)

        # If only conflict processing is requested but no conflicts exist, skip
        if not only_conflicts:
            # Extract date_taken for each file, which is needed for mutual name detection and renaming
            find_all_file_dates()

            # Identify mutual names before renaming
            search_mutual_names()

            # Check for conflicts
            mark_conflicts()
        elif conflict_exists():
            # If conflicts exist, print header and run conflict processing
            print_conflict_header()

            # Remove conflict suffixes for all files before reprocessing
            reset_conflicts()

        # Continue with renaming phase
        rename_all_files(only_conflicts)


def print_folder_title(folder: Path):
    """Print a title for the current folder being processed."""
    log.info(EQUAL * LINE_LENGTH)
    log.info(str.center(f" {folder} ", LINE_LENGTH))


def fetch_list_metadata(folder: Path, ext: str):
    """Populate the global list_metadata with Metadata objects for each file in the given folder."""
    global list_metadata

    list_metadata.clear()
    # Walk through the folder and find files matching the specified extensions,
    # then build Metadata objects for each file found
    for root, _, _ in os.walk(folder):
        cmd_dir = f'{CMD_DIR} "{root}{SLASH}*.{ext}"'

        try:
            # Execute directory listing command
            result = subprocess.check_output(
                cmd_dir,
                shell=True,
                text=True,
                stderr=subprocess.DEVNULL,
            )
            # If no files found, skip to the next folder
            print_folder_title(Path(root))

            # Build metadata objects for each file found
            for i, file in enumerate(result.splitlines()):
                meta = Metadata()
                name, ext = file.split(".", 1)
                ext = ext.lower()

                set_metadata(
                    meta,
                    folder=Path(root),
                    initial_name=name,
                    actual_name=name,
                    ext=ext,
                    no=i + 1,
                )
                list_metadata.append(meta)
        except subprocess.CalledProcessError:
            # Ignore folders with no matching files
            continue


def print_app_header():
    """Print an app header for the start of the renaming process."""
    # Log the start of the renaming process with a timestamped header
    log.info("\n" + EQUAL * LINE_LENGTH)
    log.info(
        str.center(
            f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - MEDIA RENAMER STARTED",
            LINE_LENGTH,
            " ",
        )
    )


def print_app_footer():
    """Print an app footer for the end of the renaming process."""
    # Final log entry to indicate completion of the renaming process
    log.info(EQUAL * LINE_LENGTH)
    log.info(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - MEDIA RENAMER FINISHED")
    log.info(EQUAL * LINE_LENGTH)


# YEARS = range(2005, 2027)
# BASE = Path("X:/_Media")
# YEARS = [2025, 2026]
YEARS = []
BASE = Path("C:\\Users\\aykan\\Desktop")
CMD_DIR = "dir /B /o:d"


def run_media_renamer():
    """Run the full renaming operations: fetch files, process them, and handle conflicts."""
    # Enable HEIC support
    register_heif_opener()
    # Print the application header to indicate the start of the process
    print_app_header()

    folder: Path | None = None
    # Process each year folder if YEARS is defined, otherwise process the base folder directly
    if len(YEARS) > 0:
        for yyyy in YEARS:
            log.info("\n" + str.center(f" {yyyy} ", LINE_LENGTH, EQUAL))
            folder = Path(f"{BASE}{SLASH}{yyyy}")
    else:
        folder = BASE

    for ext in FILE_EXTENSIONS:
        # Fetch files and populate metadata list, then process them for renaming
        fetch_list_metadata(folder, ext)  # type: ignore
        # Process the files for metadata extraction, conflict resolution, and renaming
        process_files()
    # Print the application footer to indicate the end of the process
    print_app_footer()


# Global variables
list_metadata: list[Metadata] = []
dict_file_counts: dict[str, int] = {}

# Start the renaming operations with logging enabled
log = logger.setup_logging(APP_NAME)
run_media_renamer()
