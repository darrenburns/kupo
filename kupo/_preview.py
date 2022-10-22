from __future__ import annotations

from pathlib import Path

from rich.syntax import Syntax
from textual.binding import Binding
from textual.geometry import Size
from textual.widgets import Static

from _directory import DirectoryListRenderable
from _files import list_files_in_dir


class Preview(Static, can_focus=True):
    COMPONENT_CLASSES = {
        "preview--body",
        "directory--meta-column",
        "directory--dir",
    }

    BINDINGS = [
        Binding("g", "top", "Home", key_display="g"),
        Binding("G", "bottom", "End", key_display="G"),
        Binding("j", "down", "Down", key_display="j"),
        Binding("k", "up", "Up", key_display="k"),
    ]

    def __init__(
        self,
        *,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ):
        super().__init__(name=name, id=id, classes=classes)
        self._content_height = None
        self._content_width = None

    def show_syntax(self, text: str, path: Path) -> None:
        lines = text.split("\n")
        self._content_height = len(lines)
        self._content_width = max(len(line) for line in lines) + len(
            str(len(lines))) + 1
        lexer = Syntax.guess_lexer(str(path), text)
        background_colour = self.get_component_styles("preview--body").background.hex
        self.update(
            Syntax(
                text,
                lexer,
                background_color=str(background_colour),
                line_numbers=True,
                indent_guides=True,
            )
        )

    def show_directory_preview(self, path: Path) -> None:
        files = list_files_in_dir(path)
        self._content_height = len(files)
        self._content_width = None
        directory_style = self.get_component_rich_style("directory--dir")
        directory = DirectoryListRenderable(
            files,
            selected_index=None,
            dir_style=directory_style,
            meta_column_style=self.get_component_rich_style("directory--meta-column"),
        )
        self.update(directory)

    def get_content_height(self, container: Size, viewport: Size, width: int) -> int:
        return max(self._content_height or 0, container.height)

    def get_content_width(self, container: Size, viewport: Size) -> int:
        if self._content_width is not None:
            return max(container.width, self._content_width)
        else:
            return super().get_content_width(container, viewport)
