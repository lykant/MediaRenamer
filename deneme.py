import os
import ffmpeg
import subprocess
from pathlib import Path
from datetime import datetime, timezone
from PIL import Image
from PIL.ExifTags import TAGS

# DIR = "X:\\_Media\\2009"
PATH = "C:\\Users\\aykan\\Desktop\\20180422-171725-0001.jpg"

FILE_EXTENSIONS = ["jpg", "heic", "gif", "mov", "mp4", "m4a"]
EXIF_TAGS = ["DateTimeOriginal", "DateTimeDigitized", "DateTime"]
FFMPEG_TAGS = ["com.apple.quicktime.creationdate", "creation_time"]

DT_FORMAT = "%Y:%m:%d %H:%M:%S"


def get_exif_tags():
    dict_tag = {}
    for id, tag in TAGS.items():
        if tag in EXIF_TAGS:
            dict_tag |= {tag: id}
    return dict_tag


def get_min(value1, value2):
    min_value = min(value1, value2) if value1 and value2 else value1 or value2
    return min_value


def get_utc_time(_time):
    if not _time:
        return None
    r_time = _time.replace(tzinfo=timezone.utc)
    return r_time


def get_exif_date(full_path):
    dict_tags = get_exif_tags()
    img = Image.open(full_path)
    exif_data = img._getexif()
    if not exif_data:
        return None

    date_taken = date_exif = None
    for tag, id in dict_tags.items():
        print(f"id, tag = {id}, {tag}")
        value = exif_data[id]
        value = str(value).strip()
        if not value:
            continue
        # tag = TAGS.get(tag_id, tag_id)

        # if tag in ["DateTimeOriginal", "DateTimeDigitized", "DateTime"]:
        value = datetime.strptime(str(value), DT_FORMAT)
        value = get_utc_time(value)
        date_exif = get_min(date_exif, value)
    date_taken = date_exif
    return date_taken


print(get_exif_date(PATH))
exit()

full_path = "C:\\Users\\aykan\\Desktop\\20240621-231757-2063.jpg"
img = Image.open(full_path)
print({TAGS.get(k, k): v for k, v in img._getexif().items()})


exit()


def get_files(in_dir):
    dict_folders = {}
    for root, _, _ in os.walk(in_dir):
        dict_files = {}
        print(f"root: {root}")
        for ext in FILE_EXTENSIONS:
            result_dir = ""
            cmd_dir = f'dir /B /on "{root}\\*.{ext}"'
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
            dict_folders |= {root: dict_files}
    return


get_files(DIR)
