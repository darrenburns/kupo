from __future__ import annotations

import functools
import math
import os.path
import re
import string
import sys
from datetime import datetime
from pathlib import Path

from rich.align import Align
from rich.columns import Columns
from rich.console import RenderableType, Console, ConsoleOptions, RenderResult
from rich.markup import escape
from rich.padding import Padding
from rich.segment import Segment
from rich.style import Style
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text
from textual import events
from textual._types import MessageTarget
from textual.app import App
from textual.geometry import Size, clamp
from textual.message import Message
from textual.reactive import Reactive
from textual.widget import Widget


def convert_size(size_bytes):
    if size_bytes == 0:
        return "0 B"
    size_name = ("B", "K", "M", "G", "T", "P", "E", "Z", "Y")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return "%s %s" % (s, size_name[i])


def octal_to_string(octal):
    result = ""
    value_letters = [(4, "r"), (2, "w"), (1, "x")]
    for digit in [int(n) for n in str(octal)]:
        for value, letter in value_letters:
            if digit >= value:
                result += letter
                digit -= value
            else:
                result += "-"
    return result


class SelectedPath(Message, bubble=True):
    def __init__(self, path: Path, sender: MessageTarget):
        self.path = path
        super().__init__(sender)


class DirectoryListRenderable:
    def __init__(
        self, files: list[Path], selected_index: int | None, filter: str = ""
    ) -> None:
        self.files = files
        self.selected_index = selected_index
        self.filter = filter

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        table = Table.grid(expand=True)
        table.add_column()
        table.add_column(justify="right")

        for index, file in enumerate(self.files):
            if not self.filter or (self.filter and re.search(self.filter, file.name)):
                if index == self.selected_index:
                    style = "bold white on #1E90FF"
                elif file.is_dir():
                    style = "#1E90FF"
                else:
                    style = ""

                file_name = escape(file.name)
                if file.is_dir():
                    file_name += "/"

                file_name = Text(file_name)
                if self.filter:
                    file_name.highlight_regex(self.filter, "#191004 on #FEA62B")

                table.add_row(file_name, convert_size(file.stat().st_size), style=style)
        yield table


class DirectoryListHeader(Widget, can_focus=False):
    num_files = Reactive(0)
    total_size_bytes = Reactive(0)

    def __init__(self, num_files: int, total_size_bytes: int, **kwargs) -> None:
        super().__init__(**kwargs)
        self.num_files = num_files
        self.total_size_bytes = total_size_bytes

    def render(self) -> RenderableType:
        size_bg = self.app.get_css_variables()["accent-darken-2"]
        return Columns(
            [
                Padding(f"{self.num_files} items", pad=(0, 1)),
                Align.right(
                    Padding(
                        convert_size(self.total_size_bytes),
                        style=f"on {size_bg}",
                        pad=(0, 1),
                    )
                ),
            ],
            expand=True,
        )


class DirectoryList(Widget, can_focus=True):
    selected_index = Reactive(0)
    has_focus = Reactive(False)
    filter = Reactive("")

    def __init__(self, path: Path, initial_active_file: Path | None = None, **kwargs):
        super().__init__(**kwargs)
        self.path = path
        self.files: list[Path] = self._list_files(path)
        self.initial_active_file = initial_active_file
        if initial_active_file:
            self.highlight_file(initial_active_file)

    def _list_files(self, path: Path) -> list[Path]:
        return list(
            sorted(list_files_in_dir(path), key=lambda p: (not p.is_dir(), p.name))
        )

    def get_content_height(self, container: Size, viewport: Size, width: int) -> int:
        return len(self.files)

    def on_focus(self, event: events.Focus):
        self.has_focus = True

    def on_blur(self, event: events.Blur):
        self.has_focus = False

    def on_key(self, event: events.Key) -> None:
        if event.key in string.digits:
            key = int(event.key)
            if key == 0:
                key = 10
            self.selected_index = self._clamp_selected_index(key - 1)
            self._report_active_path()

    def move_down(self):
        self.selected_index = max(
            0, self._clamp_selected_index(self.selected_index - 1)
        )
        self._report_active_path()

    def move_up(self):
        self.selected_index = min(
            len(self.files) - 1, self._clamp_selected_index(self.selected_index + 1)
        )
        self._report_active_path()

    def _clamp_selected_index(self, index: int) -> int:
        """Ensures the selected file index is always valid"""
        return clamp(index, 0, len(self.files) - 1)

    def update_files(self, directory: Path, active_path: Path | None = None):

        self.files = self._list_files(directory)
        self._filter_files(self.filter)
        if active_path:
            self.highlight_file(active_path)
        self.refresh(layout=True)

    def watch_filter(self, value: str) -> None:
        self.files = self._list_files(self.path)
        if value:
            self._filter_files(value)

        print(f"watch_filter {value} new files: {self.files}")
        self.selected_index = self._clamp_selected_index(self.selected_index)

    def _filter_files(self, filter: str) -> None:
        files_to_display = []
        for file in self.files:
            try:
                match = re.search(filter, file.name)
            except Exception:
                match = None
            if not filter or (filter and match):
                files_to_display.append(file)

        print(f"_filter_files {files_to_display}")
        self.files = files_to_display

    def highlight_file(self, path):
        try:
            index = self.files.index(path)
        except ValueError:
            index = 0
        self.selected_index = index

    def _report_active_path(self) -> None:
        if len(self.files) > 0:
            path = self.files[self.selected_index]
            self.emit_no_wait(SelectedPath(path, sender=self))

    def render(self) -> RenderableType:
        return DirectoryListRenderable(
            self.files, self.selected_index, filter=self.filter
        )


class DirectorySearchInfo(Widget, can_focus=False):
    matching_files = Reactive([], layout=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.css_variables = self.app.get_css_variables()
        self.success_colour = self.css_variables["success"]
        self.danger_colour = self.css_variables["error"]

    def watch_matching_files(self, value) -> None:
        if value is not None:
            self.styles.display = "block"
        else:
            self.styles.display = "none"

    def _success_styles(self):
        self.styles.height = 2
        success_border_edge = ("heavy", self.success_colour)
        self.styles.border_left = success_border_edge
        self.styles.border_right = success_border_edge

    def _danger_styles(self):
        self.styles.height = 1
        danger_border_edge = ("heavy", self.danger_colour)
        self.styles.border_left = danger_border_edge
        self.styles.border_right = danger_border_edge

    def _neutral_styles(self):
        self.styles.height = 1
        border_edge = ("heavy", "transparent")
        self.styles.border_left = border_edge
        self.styles.border_right = border_edge

    def render(self) -> RenderableType:
        if self.matching_files is None:
            self._neutral_styles()
            return Text("")

        num_matches = len(self.matching_files)
        if num_matches == 1:
            self._success_styles()
            return Text.assemble(
                (f"Press ⏎ to select file:\n ", f"bold {self.success_colour}"),
                (self.matching_files[0].name, self.success_colour),
            )
        elif num_matches == 0:
            self._danger_styles()
            return Text("No matching files", style=f"bold {self.danger_colour}")
        else:
            self._neutral_styles()
            return Text.assemble(
                (str(num_matches), Style(bold=True, dim=True)),
                (" matching files", Style(dim=True)),
            )


class AppHeader(Widget, can_focus=False):
    def __init__(self, current_path: Path, *children: Widget, **kwargs):
        self.current_path = current_path
        darken_bg = self.app.get_css_variables()["accent-darken-2"]
        self.logo = Text.from_markup(f"[on {darken_bg}] ⌒ ● ⌒ ")

        super().__init__(*children, **kwargs)

    def new_selected_path(self, path: Path):
        self.current_path = path
        self.refresh(layout=True)

    def render(self) -> RenderableType:
        current_path = Align.right(
            Text.assemble(
                Text(f"{self.current_path.parent}{os.path.sep}"),
                Text(f"{self.current_path.name}", style="bold"),
            )
        )
        return Columns([self.logo, current_path], expand=True)


class AppFooter(Widget, can_focus=False):
    def __init__(self, current_path: Path, *children: Widget, **kwargs):
        self.current_path = current_path
        super().__init__(*children, **kwargs)

    def new_selected_path(self, path: Path):
        self.current_path = path
        self.stat = self.current_path.stat()
        self.refresh(layout=True)

    def render(self) -> RenderableType:
        name = self.current_path.name
        st_mode = str(self.stat.st_mode)
        owner = self.current_path.owner()
        date_modified = datetime.fromtimestamp(self.stat.st_ctime)
        table = Table.grid(expand=True)
        table.add_column()
        table.add_column()
        table.add_row(
            Padding(
                f"[b]{escape(name)}[/] {st_mode} {owner} {date_modified.date()} {date_modified.strftime('%H:%M:%S')}",
                pad=(0, 1),
            ),
            Align.right("[b]?[/] "),
        )
        return table


class Emptiness:
    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        width = options.max_width
        height = options.height or options.max_height
        segment = Segment(f"{'╲' * width}\n")
        yield from [segment] * height


class EmptySpace(Widget):
    def __init__(self, *children: Widget, **kwargs):
        super().__init__(*children)
        self.add_class("empty_space")

    def render(self) -> RenderableType:
        return Emptiness()


@functools.lru_cache(8)
def read_text_from_path(path: Path) -> str:
    try:
        return path.read_text()
    except UnicodeDecodeError:
        return ""


class FilePreview(Widget):
    def __init__(
        self,
        current_path: Path,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ):
        self.current_path = current_path
        if current_path.is_file():
            self.file_content = read_text_from_path(current_path)
        else:
            self.file_content = ""
        super().__init__(name=name, id=id, classes=classes)

    def new_selected_path(self, path: Path):
        self.current_path = path
        if path.is_file():
            self.file_content = read_text_from_path(path)
        else:
            self.file_content = ""
        self.refresh(layout=True)  # Layout required for changes in height

    def get_content_height(self, container: Size, viewport: Size, width: int) -> int:
        if self.file_content:
            return len(self.file_content.splitlines())
        return super().get_content_height(container, viewport, width)

    def render(self) -> RenderableType:
        if self.current_path.is_file():
            self.file_content = read_text_from_path(self.current_path)
            file_name = self.current_path.name
            preview = Syntax(
                code=self.file_content,
                lexer=Syntax.guess_lexer(file_name),
                theme="monokai" if self.app.dark else "manni",
                line_numbers=True,
                indent_guides=True,
                background_color="#111111" if self.app.dark else "#f0f0f0",
            )
        elif self.current_path.is_dir():
            files = list_files_in_dir(self.current_path)
            preview = DirectoryListRenderable(
                files=files,
                selected_index=None,
            )
        else:
            preview = Emptiness()

        return preview


def list_files_in_dir(dir: Path):
    try:
        files = list(dir.iterdir())
    except OSError:
        files = []
    return files


class FilesApp(App):
    selected_path = Reactive(Path.cwd())

    def on_load(self):
        self.bind("q", "quit", "Quit")
        self.bind("j", "next_file", "Next File")
        self.bind("k", "prev_file", "Previous File")
        self.bind("l", "choose_path", "Go To Child")
        self.bind("h", "goto_parent", "Go To Parent")
        self.bind("enter", "choose_path", "Go To Child")
        self.bind("d", "toggle_dark", "Toggle Dark Mode")
        self.bind("g", "top_of_file", "Top Of File")
        self.bind("G", "bottom_of_file", "Bottom Of File")
        self.bind("?", "help", "Help")
        self.bind("/", "focus('this_directory_search')")
        self.bind("ctrl+x", "dump_state")
        self.bind("escape", "focus('this_directory')")

    def on_mount(self):
        self.dark = True
        self.selected_path = next(Path.cwd().iterdir(), Path.cwd())
        self.parent_directory = DirectoryList(
            path=self.selected_path.parent.parent,
            id="parent_directory",
            initial_active_file=self.selected_path.parent,
        )

        self.this_directory = DirectoryList(
            path=self.selected_path.parent,
            id="this_directory",
        )
        self.this_directory.focus()
        self.file_preview = FilePreview(
            current_path=self.selected_path, id="file_preview_content"
        )
        self.preview_wrapper = Widget(self.file_preview, id="file_preview_wrapper")

        self.this_directory_search = TextInput(
            placeholder="Press / to search", id="this_directory_search"
        )

        self.this_directory_search_info = DirectorySearchInfo(
            id="this_directory_search_info"
        )

        self.this_directory_header = DirectoryListHeader(
            0, 0, classes="directory_list_header", id="this_directory_header"
        )
        self.body_wrapper = Widget(
            Widget(self.parent_directory, id="parent_directory_wrapper"),
            Widget(
                self.this_directory_header,
                self.this_directory,
                self.this_directory_search,
                self.this_directory_search_info,
                id="this_directory_wrapper",
            ),
            self.preview_wrapper,
        )
        self.header = AppHeader(current_path=self.selected_path.parent)
        self.footer = AppFooter(current_path=self.selected_path.parent)
        self.mount(
            header=self.header,
            body_wrapper=self.body_wrapper,
            footer=self.footer,
        )
        self._update_ui_new_selected_path()

    def handle_selected_path(self, message: SelectedPath):
        path = message.path
        self.selected_path = path
        self.file_preview.new_selected_path(path)
        self._update_ui_new_selected_path()

    def _update_ui_new_selected_path(self):
        # Update app header and footer
        self.header.new_selected_path(self.selected_path)
        self.footer.new_selected_path(self.selected_path)

        # Update the current directory pane
        self.this_directory.update_files(
            directory=self.selected_path.parent,
            active_path=self.selected_path,
        )
        # Update the header of the current directory pane
        parent_dir = list(self.selected_path.parent.iterdir())
        parent_dir_total_size_bytes = 0
        for file in parent_dir:
            try:
                parent_dir_total_size_bytes += file.stat().st_size
            except OSError:
                pass

        self.this_directory_header.num_files = len(parent_dir)
        self.this_directory_header.total_size_bytes = parent_dir_total_size_bytes

        # Update the search info box that appears above the search box
        self.this_directory_search_info.matching_files = parent_dir

        # Update the files in the parent directory (left pane)
        self.parent_directory.update_files(
            directory=self.selected_path.parent.parent,
            active_path=self.selected_path.parent,
        )

        # Update the file preview wrapper (right pane)
        self.file_preview.new_selected_path(self.selected_path)
        self.preview_wrapper.scroll_home(animate=False)

    def action_next_file(self) -> None:
        self.this_directory.move_up()

    def action_prev_file(self) -> None:
        self.this_directory.move_down()

    def action_goto_parent(self) -> None:
        self._reset_search()
        self.log(self.selected_path, self.selected_path.parent)
        self.selected_path = self.selected_path.parent
        self._update_ui_new_selected_path()

    def _reset_search(self):
        #  Update the value in the search box, and the applied filter
        self.this_directory.filter = None
        self.this_directory_search.value = ""

    def action_choose_path(self) -> None:
        self._reset_search()
        if self.selected_path.is_dir():
            files_in_dir = sorted(
                list_files_in_dir(self.selected_path),
                key=lambda f: (not f.is_dir(), f.name),
            )
            self.selected_path = next(iter(files_in_dir), self.selected_path)
        self._update_ui_new_selected_path()

    async def action_toggle_dark(self):
        self.dark = not self.dark

    async def action_top_of_file(self):
        self.preview_wrapper.scroll_home(animate=False)

    async def action_bottom_of_file(self):
        self.preview_wrapper.scroll_end(animate=False)

    async def action_help(self):
        self.preview_wrapper.scroll_home(animate=False)
        self.file_preview.new_selected_path(
            get_install_directory() / "kupo_commands.md"
        )

    def action_dump_state(self):
        self.log(selection=self.selected_path)
        self.log(current_filter=self.this_directory.filter)
        self.log(filtered_files=self.this_directory.files)
        self.log(filtered_files_length=len(self.this_directory.files))

    def handle_changed(self, event: TextInput.Changed) -> None:
        if event.sender is self.this_directory_search:
            self.this_directory.filter = event.value
            # Find the number of files that match the regex
            if event.value:
                matches = []
                for file in list_files_in_dir(self.selected_path.parent):
                    try:
                        match = re.search(event.value, file.name)
                    except Exception:
                        continue
                    if match:
                        matches.append(file)
                self.this_directory_search_info.matching_files = matches
            else:
                self.this_directory_search_info.matching_files = None


def get_install_directory() -> Path:
    return Path(sys.modules[__name__].__file__).parent


def run_develop():
    directory = get_install_directory()
    app = FilesApp(
        css_path=directory / "kupo.css", log_path=directory / "kupo.log", watch_css=True
    )
    app.run()


def run():
    directory = get_install_directory()
    app = FilesApp(css_path=directory / "kupo.css")
    app.run()

    run_develop()


if __name__ == "__main__":
    run_develop()
