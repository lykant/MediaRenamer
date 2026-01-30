import os
from pathlib import Path


DIR = f"X:\\_Media\\2005"
TXT_WRONG_PLACE = f"X:\\wrong_place.txt"
TXT_SHORT_NAME = f"X:\\short_files.txt"
FILE_EXTENSIONS = ["jpg", "heic", "gif", "mov", "mp4", "m4a"]
wrong_place_list = list()
short_file_list = list()


for root, dirs, files in os.walk(DIR):
    for f in files:
        full_path = Path(os.path.join(root, f))
        file_ext = f.split(".", 1)[1].lower()
        if file_ext not in FILE_EXTENSIONS:
            continue

        # print(f"path={full_path}")
        # print(f"f={f},  {f[:4]}, parent={full_path.parent.name}")
        if len(f) < 20:
            short_file_list.append(str(full_path))

        if f[:4] != full_path.parent.name[:4]:
            wrong_place_list.append(f"{str(full_path)} : {full_path.parent.name}")

with open(TXT_SHORT_NAME, "w", encoding="utf-8") as f:
    for name in short_file_list:
        f.write(name + "\n")

with open(TXT_WRONG_PLACE, "w", encoding="utf-8") as f:
    for name in wrong_place_list:
        f.write(name + "\n")

print(f"Short names:\n {short_file_list}")
print(f"Wrong place files:\n {wrong_place_list}")
