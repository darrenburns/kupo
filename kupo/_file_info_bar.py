from __future__ import annotations

import stat
from datetime import datetime
from pathlib import Path

from rich.console import RenderableType
from rich.text import Text
from textual.reactive import reactive
from textual.widget import Widget


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
        modify_time = datetime.utcfromtimestamp(file_stat.st_mtime).strftime(
            "%-d %b %y %X")
        perm_string = stat.filemode(file_stat.st_mode)
        perm_string = Text.assemble(
            (perm_string[0], "b dim"),
            (perm_string[1], "yellow b"),
            (perm_string[2], "red b"),
            (perm_string[3], "green b"),
            (perm_string[4], "yellow"),
            (perm_string[5], "red"),
            (perm_string[6], "green"),
            (perm_string[7], "yellow"),
            (perm_string[8], "red"),
            (perm_string[9], "green"),
        )
        return Text.assemble(
            (file.name, "bold"),
            "  ",
            perm_string,
            "  ",
            modify_time
        )
