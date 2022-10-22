from __future__ import annotations

import asyncio
from pathlib import Path

import aiofiles
from rich.markdown import Markdown
from textual import events
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Container
from textual.screen import Screen
from textual.widgets import Static, Footer

from _directory import Directory
from _file_info_bar import CurrentFileInfoBar
from _header import Header, HeaderCurrentPath
from _preview import Preview


class Home(Screen):
    BINDINGS = [
        Binding("question_mark", "app.push_screen('help')", "Help", key_display="?"),
        Binding("q", "quit", "Exit"),
    ]

    def compose(self) -> ComposeResult:
        self._initial_cwd = Path.cwd()
        parent = Directory(
            path=self._initial_cwd.parent, id="parent-dir", classes="dir-list"
        )
        parent.can_focus = False

        yield Header()
        yield Horizontal(
            parent,
            Container(
                Directory(path=self._initial_cwd, id="current-dir", classes="dir-list"),
                id="current-dir-wrapper",
            ),
            Container(Preview(id="preview"), id="preview-wrapper"),
        )
        yield CurrentFileInfoBar()
        yield Footer()

    def on_mount(self, event: events.Mount) -> None:
        self.query_one("#parent-dir", Directory).select_path(self._initial_cwd)
        self.query_one("#current-dir").focus(scroll_visible=False)

    def on_directory_file_preview_changed(self, event: Directory.FilePreviewChanged):
        """When we press up or down to highlight different dirs or files, we
        need to update the preview on the right-hand side of the screen."""

        # Ensure the message is coming from the correct directory widget
        # TODO: Could probably add a readonly flag to Directory to prevent having this check
        self.query_one(CurrentFileInfoBar).file = event.path
        if event.sender.id == "current-dir":
            if event.path.is_file():
                asyncio.create_task(self.show_syntax(event.path))
            elif event.path.is_dir():
                self.query_one("#preview", Preview).show_directory_preview(event.path)
        self.query_one(HeaderCurrentPath).path = event.path

    def on_directory_current_dir_changed(self, event: Directory.CurrentDirChanged):
        new_dir = event.new_dir
        from_dir = event.from_dir
        self._update_directory_and_parent_widgets(new_dir, from_dir)

    def _update_directory_and_parent_widgets(
        self, new_dir: Path, from_dir: Path | None = None
    ) -> None:
        directory_widget = self.query_one("#current-dir", Directory)
        directory_widget.update_source_directory(new_dir)
        directory_widget.select_path(from_dir)

        parent_directory_widget = self.query_one("#parent-dir", Directory)
        parent_directory_widget.update_source_directory(new_dir.parent)
        parent_directory_widget.select_path(new_dir)

    async def show_syntax(self, path: Path) -> None:
        async with aiofiles.open(path, mode="r") as f:
            # TODO - if they start scrolling preview, load more than 1024 bytes.
            contents = await f.read(2048)
        self.query_one("#preview", Preview).show_syntax(contents, path)


class Help(Screen):
    BINDINGS = [
        Binding("escape,q", "app.pop_screen", "Exit Help Screen"),
    ]

    def compose(self) -> ComposeResult:
        help_path = Path(__file__).parent / "kupo_commands.md"
        help_text = help_path.read_text(encoding="utf-8")
        rendered_help = Markdown(help_text)
        yield Static(rendered_help)
        yield Footer()


class Kupo(App):
    CSS_PATH = "kupo.css"
    SCREENS = {
        "home": Home(),
        "help": Help(),
    }
    BINDINGS = []

    def on_mount(self) -> None:
        self.push_screen("home")


app = Kupo()
if __name__ == "__main__":
    app.run()
