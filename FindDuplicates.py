from collections import defaultdict
from pathlib import Path
import hashlib


def file_hash(path: Path, chunk_size: int = 8192) -> str:
    """Return SHA-256 hash of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            h.update(chunk)
    return h.hexdigest()


def find_duplicates(folder: str):
    """Return dict: hash -> list of files with that hash."""
    hashes = {}
    for path in Path(folder).rglob("*"):
        if path.is_file():
            h = file_hash(path)
            hashes.setdefault(h, []).append(str(path))
    return {h: files for h, files in hashes.items() if len(files) > 1}


def find_duplicates_fast(folder: str):
    size_groups = defaultdict(list)

    # 1) Group by file size
    for path in Path(folder).rglob("*"):
        if path.is_file():
            size_groups[path.stat().st_size].append(path)

    # 2) Hash only groups with more than 1 file
    duplicates = {}
    for size, files in size_groups.items():
        if len(files) < 2:
            continue

        for f in files:
            h = file_hash(f)
            duplicates.setdefault(h, []).append(str(f))

    return {h: f for h, f in duplicates.items() if len(f) > 1}


dupes = find_duplicates_fast(r"X:\_Media")
for h, files in dupes.items():
    print("\nDuplicate group:")
    for f in files:
        print("  ", f)
