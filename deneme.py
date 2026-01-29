import os
import subprocess
from pathlib import Path

DIR = f"X:\\_Media\\2009"
FILE_EXTENSIONS = ["jpg", "heic", "gif", "mov", "mp4", "m4a"]


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
