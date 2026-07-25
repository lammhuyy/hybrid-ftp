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