import lib.metadata as meta
import lib.util as util
import lib.constants as cons
from dataclasses import dataclass
from pathlib import Path
from datetime import date


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
    date_taken_str: str | None = None
    new_name: str | None = None
    new_full_name: str | None = None
    new_full_path: Path | None = None
    ext: str | None = None
    is_mutual: bool = cons.NO
    mutual_order: int = 0
    mutual_suffix: str = cons.DIYEZ
    has_conflict: bool = cons.NO
    conflict_suffix: str = cons.DIYEZ


def set_metadata(
    meta: meta.Metadata,
    folder: Path | None = None,
    initial_name: str | None = None,
    actual_name: str | None = None,
    date_taken: date | None = None,
    new_name: str | None = None,
    ext: str | None = None,
    is_mutual: bool | None = None,
    mutual_order: int = 0,
    mutual_suffix: str = cons.DIYEZ,
    has_conflict: bool | None = None,
    conflict_suffix: str = cons.DIYEZ,
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
    meta.date_taken_str = (
        util.date_to_string(meta.date_taken) if date_taken else meta.date_taken_str
    )
    meta.new_name = new_name or meta.new_name
    meta.ext = ext or meta.ext
    meta.mutual_suffix = (
        mutual_suffix if mutual_suffix != cons.DIYEZ else meta.mutual_suffix
    )
    meta.conflict_suffix = (
        conflict_suffix if conflict_suffix != cons.DIYEZ else meta.conflict_suffix
    )

    # Mutual group flags
    if is_mutual:
        meta.is_mutual = is_mutual
        meta.mutual_order = mutual_order
        meta.mutual_suffix = f"{cons.HYPHEN}{mutual_order:02d}"

    # Conflict flags
    meta.has_conflict = has_conflict if has_conflict is not None else meta.has_conflict
    meta.conflict_suffix = (
        cons.BLANK
        if conflict_suffix != cons.DIYEZ
        else f"{cons.DIYEZ}{meta.no:05d}" if meta.has_conflict else cons.BLANK
    )

    # Rebuild full names and paths
    set_actual_name(meta)
    set_new_name(meta)


def set_new_name(meta: Metadata):
    """
    Build the new file name and full path using:
    - date_taken_str (preferred)
    - new_name (fallback)
    - mutual suffix if part of a mutual group
    - conflict suffix if there is a conflict
    """

    # If no date and no new name, nothing to build
    if not meta.date_taken_str and not meta.new_name:
        return

    # Prefer EXIF/OS date; fallback to manually assigned new_name
    meta.new_name = meta.date_taken_str or meta.new_name

    # Append mutual and conflict suffixes if applicable
    suffix = meta.mutual_suffix if meta.mutual_suffix != cons.DIYEZ else cons.BLANK
    suffix += meta.conflict_suffix if meta.conflict_suffix != cons.DIYEZ else cons.BLANK
    meta.new_name = f"{meta.new_name}{suffix}"

    # Build full new name and path
    meta.new_full_name = util.concat_full_name(meta.new_name, meta.ext)
    meta.new_full_path = util.concat_full_path(meta.folder, meta.new_full_name)


def set_actual_name(meta: Metadata):
    """
    Build the actual_full_name and actual_full_path fields
    based on the current actual_name and extension.
    """
    # If no actual name, nothing to build
    if not meta.actual_name:
        return

    # Build full file name and full path for the actual/original file
    meta.actual_full_name = util.concat_full_name(meta.actual_name, meta.ext)
    meta.actual_full_path = util.concat_full_path(meta.folder, meta.actual_full_name)
