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
import subprocess
import lib.metadata as meta
import lib.util as util
import lib.constants as cons
import lib.message as msg
import lib.exif as exif
import lib.ffmpeg as ffmpeg
from typing import Optional
from pathlib import Path
from datetime import date
from itertools import product


# Constants
APP_NAME = Path(__file__).stem
FILE_EXTENSIONS = ["jpg", "heic", "mov", "mp4", "mpg", "gif", "m4a"]


def find_file_date(meta_obj: meta.Metadata) -> Optional[date]:
    """Determine the date taken for a file using EXIF, FFmpeg, and OS timestamps."""
    full_path = meta_obj.actual_full_path
    ext = meta_obj.ext
    date_taken = None

    # Try EXIF or FFmpeg depending on file type
    if ext in ["jpg", "heic"]:
        date_taken = exif.get_date_taken(full_path)  # type: ignore
    elif ext in ["mov", "mp4", "mpg", "gif"]:
        date_taken = ffmpeg.get_ffmpeg_date(str(full_path))

    # Always fallback to OS timestamps
    date_os = exif.get_os_date(full_path)  # type: ignore
    date_taken = exif.get_min(date_taken, date_os)  # type: ignore
    return date_taken


def os_rename(meta_obj: meta.Metadata):
    """Perform the actual filesystem rename operation."""
    os.rename(meta_obj.actual_full_path, meta_obj.new_full_path)  # type: ignore


def rename_all_files(only_conflicts: bool = cons.NO):
    """Rename a file on the filesystem, optionally only if it has conflicts."""
    global list_metadata

    # Iterate over all metadata items and attempt to rename files, logging outcomes
    for meta_obj in list_metadata:
        # If only processing conflicts, skip files that do not have a conflict
        # Otherwise skip the ones that have a conflict, since they will be processed in the next run
        if only_conflicts and not meta_obj.has_conflict:
            continue

        # Safety check
        if not meta_obj.new_full_path:
            raise msg.exc_file_not_found

        # Check if the new name is the same as the actual name to avoid unnecessary renaming
        same_name = meta_obj.new_full_name == meta_obj.actual_full_name
        if same_name:
            msg.print_name_remains_same(meta_obj)
        else:
            # Attempt to rename the file and log the outcome
            try:
                os_rename(meta_obj)
            except Exception as _:
                msg.print_rename_error(meta_obj)
                continue

            # Update metadata after rename
            msg.print_rename_message(meta_obj)
            meta.set_metadata(meta_obj, actual_name=meta_obj.new_name)


def search_mutual_names():
    """Mark files with the same date_taken as mutual."""
    global list_metadata

    # Collect all unique dates from the global media list
    unique_dates = list(
        dict.fromkeys([meta_obj.date_taken_str for meta_obj in list_metadata])
    )

    # Iterate over each unique date and file extension combination
    for date_str, ext in product(unique_dates, FILE_EXTENSIONS):
        # Filter files that have the same date_taken and extension
        list_mutual = [
            m for m in list_metadata if m.date_taken_str == date_str and m.ext == ext
        ]
        # If only one file exists for that date and extension, nothing to mark as mutual
        if len(list_mutual) <= 1:
            continue

        # Mark all files with the same date and extension as mutual
        i = 0
        for meta_obj in list_mutual:
            i += 1
            meta.set_metadata(
                meta_obj,
                is_mutual=cons.YES,
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
    for meta_obj in [m for m in list_metadata if m.has_conflict]:
        trimmed_name = util.trim_string(meta_obj.new_name, cons.DIYEZ)  # type: ignore
        meta.set_metadata(meta_obj, conflict_suffix=cons.BLANK, new_name=trimmed_name)


def mark_conflicts():
    """Identify and mark files that have naming conflicts with other files."""
    global list_metadata

    # Iterate over each file and check for naming conflicts with other files
    for meta_obj1 in list_metadata:
        # A conflict occurs when another file has the same new_full_name but
        # a different original file (different 'no')
        for meta_obj2 in list_metadata:
            if (
                meta_obj2.actual_full_name == meta_obj1.new_full_name
                and meta_obj2.no != meta_obj1.no
            ):
                # Mark the file as having a conflict if a matching name is found
                meta.set_metadata(meta_obj1, has_conflict=cons.YES)
                break  # No need to check further once a conflict is found


def find_file_counts(only_conflicts: bool = cons.NO):
    """Return the global dictionary of file counts per extension."""
    global list_metadata, dict_file_counts

    # Count files per extension
    for ext in FILE_EXTENSIONS:
        if not only_conflicts:
            count = sum(1 for item in list_metadata if item.ext == ext)
        else:
            count = sum(
                1 for item in list_metadata if item.ext == ext and item.has_conflict
            )
        dict_file_counts[ext] = count


def find_all_file_dates():
    """Extract date_taken for each file in the global metadata list."""
    global list_metadata, dict_file_counts

    # If no files to process, return early
    if len(list_metadata) == 0:
        return

    # Process each file for metadata extraction
    for meta_obj in list_metadata:
        date_taken = None

        # Print header for the current file extension when processing the first file of that type
        msg.print_processing_title(meta_obj, dict_file_counts)

        # Log processing info for the current file
        msg.print_processing_message(meta_obj)

        # Extract the date taken using the defined logic (EXIF/FFmpeg/OS)
        date_taken = find_file_date(meta_obj)

        # Update metadata with extracted date
        meta.set_metadata(meta_obj, date_taken=date_taken)

    list_metadata = sorted(list_metadata, key=lambda x: (x.new_full_name, x.no))  # type: ignore
    msg.print_separator()


def process_files():
    """Process files for metadata extraction and renaming, optionally only handling conflicts."""
    # Run the full processing pipeline for all files,
    # then optionally run only conflict processing if requested
    list_conflict_status = [cons.NO, cons.YES]

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
            msg.print_conflict_title()

            # Remove conflict suffixes for all files before reprocessing
            reset_conflicts()

        # Continue with renaming phase
        rename_all_files(only_conflicts)


def fetch_list_metadata(folder: Path, ext: str):
    """Populate the global list_metadata with Metadata objects for each file in the given folder."""
    global list_metadata

    list_metadata.clear()
    # Walk through the folder and find files matching the specified extensions,
    # then build Metadata objects for each file found
    for root, _, _ in os.walk(folder):
        cmd_dir = f'{CMD_DIR} "{root}{cons.SLASH}*.{ext}"'

        try:
            # Execute directory listing command
            result = subprocess.check_output(
                cmd_dir,
                shell=True,
                text=True,
                stderr=subprocess.DEVNULL,
            )
            # If no files found, skip to the next folder
            msg.print_folder_title(Path(root))

            # Build metadata objects for each file found
            for i, file in enumerate(result.splitlines()):
                meta_obj = meta.Metadata()
                name, ext = file.split(".", 1)
                ext = ext.lower()

                meta.set_metadata(
                    meta_obj,
                    folder=Path(root),
                    initial_name=name,
                    actual_name=name,
                    ext=ext,
                    no=i + 1,
                )
                list_metadata.append(meta_obj)
        except subprocess.CalledProcessError:
            # Ignore folders with no matching files
            continue


# BASE = Path("X:/_Media")
# YEARS = [2026, 2027]
BASE = Path("d:/Media/")
YEARS = []
CMD_DIR = "dir /B /o:d"


def run_media_renamer():
    """Run the full renaming operations: fetch files, process them, and handle conflicts."""

    def run_folder(folder: Path):
        """Run the renaming operations for a single folder."""
        for ext in FILE_EXTENSIONS:
            # Fetch files and populate metadata list, then process them for renaming
            fetch_list_metadata(folder, ext)  # type: ignore
            # Process the files for metadata extraction, conflict resolution, and renaming
            process_files()

    # Print the application header to indicate the start of the process
    msg.print_app_header()

    folder: Path | None = None
    # Process each year folder if YEARS is defined, otherwise process the base folder directly
    if len(YEARS) > 0:
        for yyyy in YEARS:
            folder = Path(f"{BASE}{cons.SLASH}{yyyy}")
            run_folder(folder)
    else:
        folder = BASE
        run_folder(folder)

    # Print the application footer to indicate the end of the process
    msg.print_app_footer()


# Global variables
list_metadata: list[meta.Metadata] = []
dict_file_counts: dict[str, int] = {}

# Start the renaming operations with logging enabled
msg.setup_logger(APP_NAME)
run_media_renamer()
