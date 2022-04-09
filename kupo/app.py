from __future__ import annotations

import math
import os.path
from datetime import datetime
from pathlib import Path

from rich.align import Align
from rich.console import RenderableType, Console, ConsoleOptions, RenderResult
from rich.markup import escape
from rich.padding import Padding
from rich.segment import Segment
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text
from textual import events
from textual._types import MessageTarget
from textual.app import App
from textual.message import Message
from textual.reactive import Reactive
from textual.widget import Widget


# TODO: Create app with no on_mount and it RecursionErrors

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
    # Iterate over each of the digits in octal
    for digit in [int(n) for n in str(octal)]:
        # Check for each of the permissions values
        for value, letter in value_letters:
            if digit >= value:
                result += letter
                digit -= value
            else:
                result += '-'
    return result


class SelectedPath(Message, bubble=True):
    def __init__(self, path: Path, sender: MessageTarget):
        self.path = path
        super().__init__(sender)


class DirectoryListRenderable:
    def __init__(self, files: list[Path], selected_index: int | None) -> None:
        self.files = files
        self.selected_index = selected_index

    def __rich_console__(self, console: Console,
                         options: ConsoleOptions) -> RenderResult:
        table = Table.grid(expand=True)
        table.add_column()
        table.add_column(justify="right")
        num_files = len(self.files)

        total_size_bytes = 0
        for file in self.files:
            try:
                total_size_bytes += file.stat().st_size
            except OSError:
                pass
        table.add_row(Padding(f"{num_files} items", pad=(0, 1)),
                      convert_size(total_size_bytes),
                      style="white on #1c3663")
        for index, file in enumerate(self.files):
            if index == self.selected_index:
                style = "bold white on blue"
            elif file.is_dir():
                style = "cyan"
            else:
                style = ""

            file_name = escape(file.name)
            if file.is_dir():
                file_name += "/"
            table.add_row(Padding(file_name, pad=(0, 1)),
                          convert_size(file.stat().st_size),
                          style=style)
        yield table


class DirectoryList(Widget, can_focus=True):
    selected_index = Reactive(0)
    has_focus = Reactive(False)

    def __init__(self, *children: Widget, path: Path,
                 initial_active_file: Path | None = None,
                 **kwargs):
        super().__init__(*children, **kwargs)
        self.path = path
        self.files: list[Path] = [file for file in list_files_in_dir(self.path)]
        self.initial_active_file = initial_active_file
        if initial_active_file:
            self.highlight_file(initial_active_file)

    def on_focus(self, event: events.Focus):
        self.has_focus = True

    def on_blur(self, event: events.Blur):
        self.has_focus = False

    def move_down(self):
        self.selected_index = max(0, self.selected_index - 1)
        self._report_active_path()

    def move_up(self):
        self.selected_index = min(len(self.files) - 1, self.selected_index + 1)
        self._report_active_path()

    def update_files(self, directory: Path, active_path: Path | None = None):
        self.files = list(
            sorted(list_files_in_dir(directory),
                   key=lambda p: (not p.is_dir(), p.name)))
        if active_path:
            self.highlight_file(active_path)
        self.styles.height = float(len(self.files))
        self.refresh(layout=True)

    def highlight_file(self, path):
        try:
            index = self.files.index(path)
        except ValueError:
            index = 0
        self.selected_index = index

    def _report_active_path(self) -> None:
        path = self.files[self.selected_index]
        self.emit_no_wait(SelectedPath(path, sender=self))

    def render(self) -> RenderableType:
        return Padding(DirectoryListRenderable(self.files, self.selected_index), pad=0)


class AppHeader(Widget):
    def __init__(self, current_path: Path, *children: Widget, **kwargs):
        self.current_path = current_path
        super().__init__(*children, **kwargs)

    def new_selected_path(self, path: Path):
        self.current_path = path
        self.refresh(layout=True)

    def render(self) -> RenderableType:
        return Padding(
            Text.assemble(Text(f"{self.current_path.parent}{os.path.sep}"),
                          Text(f"{self.current_path.name}", style="bold")),
            pad=(0, 1),
        )


class AppFooter(Widget):
    def __init__(self, current_path: Path, *children: Widget, **kwargs):
        self.current_path = current_path
        super().__init__(*children, **kwargs)

    def new_selected_path(self, path: Path):
        self.current_path = path
        self.refresh(layout=True)

    def render(self) -> RenderableType:
        name = self.current_path.name
        st_mode = self.current_path.stat().st_mode
        st_mode = octal_to_string(st_mode)
        owner = self.current_path.owner()
        date_modified = datetime.fromtimestamp(self.current_path.stat().st_ctime)
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


def read_text_from_path(path: Path) -> str:
    try:
        return path.read_text()
    except UnicodeDecodeError:
        return ""


class FilePreview(Widget):
    def __init__(self, *children: Widget, current_path: Path, **kwargs):
        self.current_path = current_path
        super().__init__(*children, **kwargs)

    def new_selected_path(self, path: Path):
        self.current_path = path
        self.refresh(layout=True)

    def render(self) -> RenderableType:
        if self.current_path.is_file():
            preview = Syntax(
                code=read_text_from_path(self.current_path),
                lexer=Syntax.guess_lexer(self.current_path.name),
                theme="monokai" if self.app.dark else "manni",
                line_numbers=True,
                indent_guides=True,
                background_color="#111111" if self.app.dark else "#f0f0f0"
            )
            lines = preview.code.splitlines()
            self.styles.height = float(len(lines) + 1)
            # self.styles.width = float(max(len(line) for line in lines))
        elif self.current_path.is_dir():
            files = list_files_in_dir(self.current_path)
            preview = DirectoryListRenderable(files=files, selected_index=None)
            self.styles.height = float(len(files) + 1)
        else:
            preview = Emptiness()

        return Padding(preview, pad=0)


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

    async def on_mount(self):
        self.dark = True

        self.parent_directory = DirectoryList(
            path=self.selected_path.parent.parent,
            id="parent_directory",
            initial_active_file=self.selected_path.parent,
        )
        self.this_directory = DirectoryList(
            path=self.selected_path.parent,
            id="this_directory",
        )

        self.file_preview = FilePreview(current_path=self.selected_path,
                                        id="file_preview_content")
        self.preview_wrapper = Widget(self.file_preview, id="file_preview_wrapper")
        wrapper = Widget(
            self.parent_directory,
            self.this_directory,
            self.preview_wrapper,
        )
        self.header = AppHeader(current_path=self.selected_path.parent)
        self.footer = AppFooter(current_path=self.selected_path.parent)
        self.mount(
            header=self.header,
            body_wrapper=wrapper,
            footer=self.footer,
        )
        await self.set_focus(self.this_directory)
        self._update_ui_new_selected_path()

    def handle_selected_path(self, message: SelectedPath):
        path = message.path
        self.selected_path = path
        self.file_preview.new_selected_path(path)
        self._update_ui_new_selected_path()

    def _update_ui_new_selected_path(self, previous_path=None):
        self.header.new_selected_path(self.selected_path)
        self.footer.new_selected_path(self.selected_path)
        self.this_directory.update_files(
            directory=self.selected_path.parent,
            active_path=self.selected_path,
        )
        self.parent_directory.update_files(
            directory=self.selected_path.parent.parent,
            active_path=self.selected_path.parent,
        )
        self.file_preview.new_selected_path(self.selected_path)
        self.preview_wrapper.scroll_home(animate=False)
        self.refresh(layout=True)

    async def on_key(self, event) -> None:
        await self.dispatch_key(event)

    def key_j(self, event: events.Click) -> None:
        self.this_directory.move_up()

    def key_k(self, event: events.Click) -> None:
        self.this_directory.move_down()

    def key_h(self, event: events.Click) -> None:
        previous_path = self.selected_path
        self.selected_path = self.selected_path.parent
        self._update_ui_new_selected_path(previous_path=previous_path)

    def key_l(self, event: events.Click) -> None:
        self.log(self.selected_path)
        if self.selected_path.is_dir():
            files_in_dir = sorted(list_files_in_dir(self.selected_path),
                                  key=lambda f: (not f.is_dir(), f.name))
            self.selected_path = next(iter(files_in_dir), self.selected_path)
        self._update_ui_new_selected_path(self.selected_path)

    def key_d(self):
        self.dark = not self.dark

    def key_g(self):
        self.preview_wrapper.scroll_home(animate=False)

    def key_G(self):
        self.preview_wrapper.scroll_end(animate=False)


def run():
    FilesApp.run(css_file="files.css", log="textual.log")


if __name__ == '__main__':
    run()
