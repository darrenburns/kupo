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
        modify_time = datetime.utcfromtimestamp(file_stat.st_mtime).strftime(
            "%-d %b %y %H:%M")
        perm_string = stat.filemode(file_stat.st_mode)
        background = self.styles.background
        background_dark = background.lighten(amount=.035).hex
        perm_string = Text.assemble(
            (perm_string[0], "b dim"),
            (perm_string[1], f"yellow b on {background_dark}"),
            (perm_string[2], f"red b on {background_dark}"),
            (perm_string[3], f"green b on {background_dark}"),
            (perm_string[4], f"yellow"),
            (perm_string[5], f"red"),
            (perm_string[6], f"green"),
            (perm_string[7], f"yellow on {background_dark}"),
            (perm_string[8], f"red on {background_dark}"),
            (perm_string[9], f"green on {background_dark}"),
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
