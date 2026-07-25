import os
import stat
import time
from pathlib import Path

FILE_MODE_MAP = {
    stat.S_IFDIR: "d",
    stat.S_IFREG: "-",
    stat.S_IFLNK: "l",
}


PERM_CHARS = ["r", "w", "x"] * 3
PERM_BITS = [
    stat.S_IRUSR, stat.S_IWUSR, stat.S_IXUSR,
    stat.S_IRGRP, stat.S_IWGRP, stat.S_IXGRP,
    stat.S_IROTH, stat.S_IWOTH, stat.S_IXOTH,
]

def format_mode(mode):
    type_char = FILE_MODE_MAP.get(stat.S_IFMT(mode), "?")
    perms = ""
    for i, bit in enumerate(PERM_BITS):
        if mode & bit:
            perms += PERM_CHARS[i]
        else:
            perms += "-"
    return type_char + perms


def list_dir(abs_path):
    entries = []
    try:
        names = sorted(os.listdir(abs_path))
    except PermissionError:
        return None
    for name in names:
        full = os.path.join(abs_path, name)
        try:
            st = os.stat(full)
            mode_str = format_mode(st.st_mode)
            size = st.st_size
            mtime = time.strftime("%Y-%m-%d %H:%M", time.localtime(st.st_mtime))
            entries.append(f"{mode_str} 1 owner {size:>8} {mtime} {name}")
        except OSError:
            entries.append(f"?????????? 1 owner ????????? ???? {name}")
    return entries

def list_names(abs_path):
    try:
        return sorted(os.listdir(abs_path))
    except OSError:
        return None


def make_dir(abs_path):
    os.makedirs(abs_path, exist_ok=True)
    return True


def remove_dir(abs_path):
    os.rmdir(abs_path)
    return True


def delete_file(abs_path):
    os.remove(abs_path)
    return True


def rename(abs_from, abs_to):
    os.rename(abs_from, abs_to)
    return True

def file_size(abs_path):
    return os.path.getsize(abs_path)


def file_mtime(abs_path):
    return time.strftime("%Y%m%d%H%M%S", time.localtime(os.path.getmtime(abs_path)))


def exists(abs_path):
    return os.path.exists(abs_path)


def is_dir(abs_path):
    return os.path.isdir(abs_path)


def is_file(abs_path):
    return os.path.isfile(abs_path)

def generate_unique_path(abs_dir):
    import random
    while True:
        ts = time.strftime("%Y%m%d%H%M%S")
        suffix = "".join(random.choices("abcdefghijklmnopqrstuvwxyz0123456789", k=6))
        name = f"file_{ts}_{suffix}"
        full = os.path.join(abs_dir, name)
        if not os.path.exists(full):
            return full, name
