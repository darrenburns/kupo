from __future__ import annotations

import math
import os
from pathlib import Path


def convert_size(size_bytes: int) -> str:
    if size_bytes == 0:
        return " 0[dim]B"
    size_name = ("B", "K", "M", "G", "T", "P", "E", "Z", "Y")
    index = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, index)
    number = round(size_bytes / p, 2)
    unit = size_name[index]
    return f"{number:.0f}[dim]{unit}[/]"


def list_files_in_dir(dir: Path) -> list[Path]:
    try:
        files = sorted(list(dir.iterdir()), key=_directory_sorter)
    except OSError:
        files = []
    return files


def _directory_sorter(path: Path) -> tuple[bool, bool, str]:
    name = path.name
    return not path.is_dir(), not name.startswith("."), name


def _count_files(dir: Path) -> int | None:
    """Return the number of files in a directory.
    Return None if we can't (e.g. permission error)"""
    try:
        return len([1 for x in os.scandir(dir)])
    except PermissionError:
        return None


def rm_tree(pth: Path) -> None:
    for child in pth.iterdir():
        if child.is_file():
            child.unlink()
        else:
            rm_tree(child)
    pth.rmdir()
