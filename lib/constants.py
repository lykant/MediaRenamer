from pathlib import Path

# Constants used across the MediaRenamer application
SLASH = "\\"
DIYEZ = "#"
EQUAL = "="
HYPHEN = "-"
BLANK = ""
ENTER = "\n"

YES = True
NO = False
NAME_LENGTH = 15
LINE_LENGTH = 60
NAME_FORMAT = "%Y%m%d-%H%M%S"
DT_FORMAT = "%Y:%m:%d %H:%M:%S"
ISO_FORMAT = "%Y-%m-%d %H:%M:%S"

IMAGE_EXTENSIONS = ["jpg", "heic"]
VIDEO_EXTENSIONS = ["mov", "mp4", "mpg", "gif", "m4a"]
FILE_EXTENSIONS = IMAGE_EXTENSIONS + VIDEO_EXTENSIONS
BASE = Path("d:/Media/")
