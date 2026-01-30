import os
import ffmpeg
import subprocess
from pathlib import Path
from datetime import datetime, timezone
from PIL import Image
from PIL.ExifTags import TAGS
from pillow_heif import register_heif_opener


# Constants
NAME_FORMAT = "%Y%m%d-%H%M%S"
DT_FORMAT = "%Y:%m:%d %H:%M:%S"
ISO_FORMAT = "%Y-%m-%d %H:%M:%S"
YEARS = range(2005, 2027)
DIR = r"X:\_Media"
SLASH = "\\"

FILE_EXTENSIONS = ["jpg", "heic", "gif", "mov", "mp4", "m4a"]
EXIF_TAGS = ["DateTimeOriginal", "DateTimeDigitized", "DateTime"]
FFMPEG_TAGS = ["com.apple.quicktime.creationdate", "creation_time"]
DICT_TAGS = dict()


def concat_full_name(file_name, ext, no=None):
    full_name = f"{file_name}-{no:04d}.{ext}" if no else f"{file_name}.{ext}"
    return full_name


def concat_full_path(in_dir, file_name, ext=None, no=None):
    full_name = (
        concat_full_name(file_name, ext, no)
        if no
        else concat_full_name(file_name, ext) if ext else file_name
    )
    full_path = Path(SLASH.join([in_dir, full_name]))
    return full_path


def date_to_str(date_obj):
    date_taken = date_obj.strftime(NAME_FORMAT) if date_obj else None
    return date_taken


def get_min(value1, value2):
    min_value = min(value1, value2) if value1 and value2 else value1 or value2
    return min_value


def get_exif_tags():
    dict_tag = {}
    for id, tag in TAGS.items():
        if tag in EXIF_TAGS:
            dict_tag |= {tag: id}
    return dict_tag


def get_single_file_names(in_dir, old_name, new_name, ext, no=None):
    old_full_name = concat_full_name(old_name, ext)
    old_full_path = concat_full_path(in_dir, old_full_name)
    new_full_name = concat_full_name(new_name, ext, no)
    new_full_path = concat_full_path(in_dir, new_full_name)

    dict_single_file_names = {
        "dir": in_dir,
        "old_name": old_name,
        "old_full_name": old_full_name,
        "old_full_path": old_full_path,
        "new_name": new_name,
        "new_full_name": new_full_name,
        "new_full_path": new_full_path,
        "ext": ext,
    }
    return dict_single_file_names


def get_files(in_dir):
    dict_folder = {}
    for root, _, _ in os.walk(in_dir):
        dict_files = {}
        for ext in FILE_EXTENSIONS:
            result_dir = ""
            cmd_dir = f'dir /B /on "{root}{SLASH}*.{ext}"'
            try:
                result_dir = subprocess.check_output(
                    cmd_dir, shell=True, text=True, stderr=subprocess.DEVNULL
                )
                dict_files |= {
                    file: i + 1 for i, file in enumerate(result_dir.splitlines())
                }
            except subprocess.CalledProcessError as e:
                continue
        if len(dict_files) > 0:
            dict_folder |= {root: dict_files}
    return dict_folder


def get_utc_time(_time):
    if not _time:
        return None
    r_time = _time.replace(tzinfo=timezone.utc)
    return r_time


def get_os_date(full_path):
    c_time = datetime.fromtimestamp(os.path.getctime(full_path))
    c_time = get_utc_time(c_time)
    m_time = datetime.fromtimestamp(os.path.getmtime(full_path))
    m_time = get_utc_time(m_time)

    # OS date cannot be empty.
    date_taken = min(c_time, m_time)
    return date_taken


def get_exif_date(full_path):
    global DICT_TAGS
    img = Image.open(full_path)
    exif_data = img._getexif()
    if not exif_data:
        return None

    date_taken = date_exif = None
    for _, id in DICT_TAGS.items():
        try:
            value = exif_data[id]
        except Exception as e:
            continue
        value = str(value).strip()
        if not value:
            continue
        value = datetime.strptime(str(value), DT_FORMAT)
        value = get_utc_time(value)
        date_exif = get_min(date_exif, value)
    date_taken = date_exif
    return date_taken


def get_ffmpeg_time(full_path):
    probe = ffmpeg.probe(full_path)
    format_tags = probe.get("format", {}).get("tags", {})

    date_taken = date_ffmpeg = None
    for tag in FFMPEG_TAGS:
        value = format_tags.get(tag)
        if value:
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
            value = get_utc_time(value)
            date_ffmpeg = get_min(date_ffmpeg, value)
    date_taken = date_ffmpeg
    return date_taken


def os_rename(old_full_path, new_full_path):
    try:
        os.rename(old_full_path, new_full_path)
    except Exception as e:
        raise e


def find_date_taken(full_path, file_ext):
    date_taken = None
    if file_ext in ["jpg", "heic", "m4a"]:
        date_taken = get_exif_date(full_path)
    elif file_ext in ["mov", "mp4", "gif"]:
        date_taken = get_ffmpeg_time(full_path)

    date_os = get_os_date(full_path)
    date_taken = get_min(date_taken, date_os)
    return date_taken


def rename_file(dict_single_file_names):
    (old_full_name, new_full_name) = (
        dict_single_file_names["old_full_name"],
        dict_single_file_names["new_full_name"],
    )
    if new_full_name == old_full_name:
        print(f"File names are identical same: {new_full_name}")
        return

    (old_full_path, new_full_path) = (
        dict_single_file_names["old_full_path"],
        dict_single_file_names["new_full_path"],
    )
    os_rename(old_full_path, new_full_path)
    print(f"Renamed to: {new_full_name}")


def process_file(in_dir, file_name, file_ext, file_no=None):
    full_path = concat_full_path(in_dir, file_name, file_ext)
    date_taken = date_to_str(find_date_taken(full_path, file_ext))
    if not date_taken:
        print(f"No date found for file: {file_name}.")
        return

    dict_single_file_names = get_single_file_names(
        in_dir, file_name, date_taken, file_ext, file_no
    )
    rename_file(dict_single_file_names)


def run_media_renamer(dict_folder):
    i = 0
    for folder, files in dict_folder.items():
        for full_name, file_no in files.items():
            i += 1
            print(f"{i:4d}- Processing file: {full_name}")
            file_name = full_name.split(".", 1)[0]
            file_ext = full_name.split(".", 1)[1].lower()
            if file_ext not in FILE_EXTENSIONS:
                raise f"Skipping unsupported file type: {file_ext}"
            process_file(folder, file_name, file_ext, file_no)


# Main Execution
register_heif_opener()
DICT_TAGS = get_exif_tags()

for yyyy in YEARS:
    print("\n" + str.center(f"{yyyy}", 80, "*"))
    dir_year = f"{DIR}{SLASH}{yyyy}"
    dict_folder = get_files(dir_year)
    run_media_renamer(dict_folder)

# # For Test
# dir_year = "C:\\Users\\aykan\\Desktop"
# dict_folder = get_files(dir_year)
# run_media_renamer(dict_folder)
