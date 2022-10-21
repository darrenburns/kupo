from __future__ import annotations

import re
from pathlib import Path

from rich.console import RenderableType, RenderResult, Console, ConsoleOptions
from rich.markup import escape
from rich.style import Style
from rich.table import Table
from rich.text import Text
from textual.binding import Binding
from textual.dom import DOMNode
from textual.geometry import clamp
from textual.message import Message
from textual.widget import Widget

from _files import convert_size, list_files_in_dir


class DirectoryListRenderable:
    def __init__(
        self,
        files: list[Path],
        selected_index: int | None,
        filter: str = "",
        dir_style: Style | None = None,
        highlight_style: Style | None = None,
        highlight_dir_style: Style | None = None,
        meta_column_style: Style | None = None,
        highlight_meta_column_style: Style | None = None,

    ) -> None:
        self.files = files
        self.selected_index = selected_index
        self.filter = filter
        self.dir_style = dir_style
        self.highlight_style = highlight_style
        self.highlight_dir_style = highlight_dir_style
        self.meta_column_style = meta_column_style
        self.highlight_meta_column_style = highlight_meta_column_style

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        table = Table.grid(expand=True)
        table.add_column()
        table.add_column(justify="right", max_width=8)

        for index, file in enumerate(self.files):
            is_dir = file.is_dir()
            if not self.filter or (self.filter and re.search(self.filter, file.name)):
                if index == self.selected_index:
                    meta_style = self.highlight_meta_column_style
                    if is_dir:
                        style = self.highlight_dir_style or "bold red on #1E90FF"
                    else:
                        style = self.highlight_style or "bold red on #1E90FF"
                else:
                    meta_style = self.meta_column_style
                    if is_dir:
                        style = self.dir_style
                    else:
                        style = ""

                file_name = escape(file.name)
                if is_dir:
                    file_name += "/"

                file_name = Text(file_name, style=style)
                if file_name.plain.startswith("."):
                    file_name.stylize(Style(dim=True))
                if self.filter:
                    file_name.highlight_regex(self.filter, "#191004 on #FEA62B")

                table.add_row(
                    file_name,
                    Text.from_markup(convert_size(file.stat().st_size),
                                     style=meta_style),
                )
        yield table


class Directory(Widget, can_focus=True):
    COMPONENT_CLASSES = {
        "directory--dir",
        "directory--highlighted",
        "directory--highlighted-dir",
        "directory--meta-column",
        "directory--highlighted-meta-column",
    }
    BINDINGS = [
        Binding("l,right", "choose_path", "Go"),
        Binding("h,left", "goto_parent", "Out"),
        Binding("j,down", "next_file", "Next"),
        Binding("k,up", "prev_file", "Prev"),
    ]

    def __init__(
        self,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
        path: Path | None = None,
    ):
        """
        Args:
            path (Path | None): The Path of the directory to display contents of.
        """
        super().__init__(name=name, id=id, classes=classes)
        self.path = path or Path.cwd()
        self._files = list_files_in_dir(self.path)
        self._selected_index = 0

    @property
    def selected_index(self):
        return self._selected_index

    @selected_index.setter
    def selected_index(self, new_value: int):
        self._selected_index = self._clamp_index(new_value)
        selected_file = self._files[self._selected_index]
        self.emit_no_wait(Directory.FilePreviewChanged(self, selected_file))
        self.refresh(layout=True)

    def action_next_file(self):
        self.selected_index += 1

    def action_prev_file(self):
        self.selected_index -= 1

    def action_choose_path(self):
        if self.current_highlighted_path.is_dir():
            self.emit_no_wait(
                Directory.CurrentDirChanged(self, new_dir=self.current_highlighted_path,
                                            from_dir=None))

    def action_goto_parent(self):
        self.emit_no_wait(Directory.CurrentDirChanged(self, new_dir=self.path.parent,
                                                      from_dir=self.path))

    def _clamp_index(self, new_index: int) -> int:
        """Ensure the selected index stays within range"""
        return clamp(new_index, 0, len(self._files) - 1)

    @property
    def current_highlighted_path(self):
        return self._files[self.selected_index]

    def update_source_directory(self, new_path: Path | None) -> None:
        if new_path is not None:
            self.path = new_path
            self._files = list_files_in_dir(new_path)
        self.selected_index = 0 if len(self._files) > 0 else None

    def select_path(self, path: Path):
        print(f"selecting path {path}")
        if path is None:
            self.selected_index = 0
            return

        try:
            print(self._files)
            print(path)
            index = self._files.index(path)
        except ValueError:
            index = 0
        self.selected_index = index

    def render(self) -> RenderableType:
        dir_style = self.get_component_rich_style("directory--dir")
        highlight_style = self.get_component_rich_style("directory--highlighted")
        highlight_meta_column_style = self.get_component_rich_style(
            "directory--highlighted-meta-column")
        meta_column_style = self.get_component_rich_style(
            "directory--meta-column")
        highlight_dir_style = self.get_component_rich_style(
            "directory--highlighted-dir")
        return DirectoryListRenderable(
            files=self._files,
            selected_index=self.selected_index,
            filter="",
            dir_style=dir_style,
            highlight_style=highlight_style,
            highlight_dir_style=highlight_dir_style,
            meta_column_style=meta_column_style,
            highlight_meta_column_style=highlight_meta_column_style,
        )

    class CurrentDirChanged(Message, bubble=True):
        def __init__(self, sender: DOMNode, new_dir: Path,
                     from_dir: Path | None) -> None:
            """
            Args:
                sender: The sending node
                new_dir: The new active current dir
                from_dir: Only relevant when we step up the file hierarchy,
                    for ensuring initial selection in parent starts at correct place.
            """
            self.new_dir = new_dir
            self.from_dir = from_dir
            super().__init__(sender)

    class FilePreviewChanged(Message, bubble=True):
        """Should be sent to the app when the selected file is changed."""

        def __init__(self, sender: DOMNode, path: Path) -> None:
            self.path = path
            super().__init__(sender)
