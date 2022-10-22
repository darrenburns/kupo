from __future__ import annotations

import math
from pathlib import Path


def convert_size(size_bytes):
    if size_bytes == 0:
        return " 0[dim]B"
    size_name = ("B", "K", "M", "G", "T", "P", "E", "Z", "Y")
    index = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, index)
    number = round(size_bytes / p, 2)
    unit = size_name[index]
    return f" {number:.0f}[dim]{unit}"


def list_files_in_dir(dir: Path) -> list[Path]:
    try:
        files = sorted(list(dir.iterdir()), key=_directory_sorter, reverse=True)
    except OSError:
        files = []
    return files


def _directory_sorter(path: Path) -> tuple[bool, bool, str]:
    name = path.name
    return (path.is_dir(), name.startswith("."), name)
