import lib.constants as cons
from typing import Optional
from pathlib import Path
from datetime import date


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
    date_taken = _date.strftime(cons.NAME_FORMAT) if _date else None
    return date_taken
