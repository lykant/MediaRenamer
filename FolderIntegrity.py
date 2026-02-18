"""
Media Folder Integrity Checker
------------------------------

Scans a media directory recursively and identifies:
1. Files with unusually short base names.
2. Files placed in the wrong folder based on naming conventions.

Results are written to:
- short_files.txt
- wrong_place.txt
"""

import os
import lib.constants as cons
from pathlib import Path


FOLDER = cons.BASE
TXT_WRONG_PLACE = f"{FOLDER}wrong_place.txt"
TXT_SHORT_NAME = f"{FOLDER}short_files.txt"


def is_valid_media_file(file_name: str) -> bool:
    """Return True if the file extension is one of the supported media types."""
    return file_name.lower().split(".")[-1] in cons.FILE_EXTENSIONS


def is_short_name(file_name: str, min_length: int = cons.NAME_LENGTH) -> bool:
    """Return True if the base name (without extension) is shorter than min_length."""
    base = file_name.split(".", 1)[0]
    return len(base) < min_length


def is_wrong_place(file_name: str, parent_folder: str) -> bool:
    """
    Return True if the file's first 4 characters do not match
    the parent folder's first 4 characters.
    """
    return file_name[:4] != parent_folder[:4]


def scan_media_folder(base_folder: Path):
    """
    Walk through the folder recursively and collect:
    - short file names
    - wrongly placed files
    """
    short_files = []
    wrong_place_files = []

    for root, _, files in os.walk(base_folder):
        print(f"Scanning: {root}")
        folder_prefix = Path(root).name[:4]

        for f in files:
            full_path = Path(root) / f
            if not is_valid_media_file(f):
                continue
            if is_short_name(f):
                short_files.append(str(full_path))
            if is_wrong_place(f, folder_prefix):
                wrong_place_files.append(f"{full_path} : {folder_prefix}")

    return short_files, wrong_place_files


def write_list_to_file(path: str, items: list[str]):
    """Write each item in the list to a text file, one per line."""
    with open(path, "w", encoding="utf-8") as f:
        for item in items:
            f.write(item + "\n")


def main():
    """Main execution flow for scanning and reporting."""
    short_files, wrong_place_files = scan_media_folder(FOLDER)

    write_list_to_file(TXT_SHORT_NAME, short_files)
    write_list_to_file(TXT_WRONG_PLACE, wrong_place_files)

    print(f"Number of short names: {len(short_files)}")
    print(f"Number of wrong place files: {len(wrong_place_files)}")


if __name__ == "__main__":
    main()
