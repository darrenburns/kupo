from __future__ import annotations

import stat
from datetime import datetime
from pathlib import Path

from rich.console import RenderableType
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
            "%-d %b %y")
        return f"[b]{file.name}[/] " \
               f"[dim]{stat.filemode(file_stat.st_mode)} " \
               f"{modify_time}"
