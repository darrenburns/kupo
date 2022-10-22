from __future__ import annotations

import stat
from datetime import datetime
from pathlib import Path

from rich.console import RenderableType
from rich.text import Text
from textual.reactive import reactive
from textual.widget import Widget

from _files import convert_size


class CurrentFileInfoBar(Widget):
    file: Path | None = reactive(None)

    def watch_file(self, new_file: Path | None) -> None:
        if new_file is None:
            self.display = False
        else:
            self.display = True

    def render(self) -> RenderableType:
        file = self.file
        file_stat = file.stat()
        modify_time = datetime.fromtimestamp(file_stat.st_mtime).strftime(
            "%-d %b %y %H:%M")
        perm_string = stat.filemode(file_stat.st_mode)
        perm_string = Text.assemble(
            (perm_string[0], "b dim"),
            (perm_string[1],
             f"yellow b" if perm_string[1] == "r" else "dim"),
            (perm_string[2],
             f"red b" if perm_string[2] == "w" else "dim"),
            (perm_string[3],
             f"green b" if perm_string[3] == "x" else "dim"),
            (perm_string[4], "yellow b" if perm_string[4] == "r" else "dim"),
            (perm_string[5], "red b" if perm_string[5] == "w" else "dim"),
            (perm_string[6], "green b" if perm_string[6] == "x" else "dim"),
            (perm_string[7],
             f"b yellow" if perm_string[7] == "r" else "dim"),
            (perm_string[8],
             f"b red" if perm_string[8] == "w" else "dim"),
            (perm_string[9],
             f"b green" if perm_string[9] == "x" else "dim"),
        )
        assembled = [
            perm_string,
            (" ╲ ", "dim cyan"),
        ]

        if file.is_file():
            assembled += [
                Text.from_markup(convert_size(file.stat().st_size)),
                (" ╲ ", "dim cyan"),
            ]

        assembled += [
            modify_time,
            (" ╲ ", "dim cyan"),
            file.owner(),
            (" ╲ ", "dim cyan"),
            file.group(),
        ]

        return Text.assemble(*assembled)
