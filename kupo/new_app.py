from __future__ import annotations

import asyncio
from asyncio import Task
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
from _header import Header
from _preview import Preview


class Home(Screen):
    BINDINGS = [
        Binding("enter", "choose_path", "Go"),
        Binding("g", "top_of_file", "Top"),
        Binding("G", "bottom_of_file", "Bottom"),
        Binding("question_mark", "app.push_screen('help')", "Help", key_display="?"),
        Binding("ctrl+c", "quit", "Exit"),
    ]

    _update_preview_task: Task | None = None

    def compose(self) -> ComposeResult:
        cwd = Path.cwd()
        parent = Directory(path=cwd.parent, id="parent-dir", classes="dir-list")
        parent.can_focus = False

        yield Header()
        yield Horizontal(
            parent,
            Directory(path=cwd, id="current-dir", classes="dir-list"),
            Container(Preview(id="preview"), id="preview-wrapper"),
        )
        yield Footer()

    def on_mount(self, event: events.Mount) -> None:
        self.query_one("#current-dir").focus(scroll_visible=False)

    def on_directory_file_preview_changed(self, event: Directory.FilePreviewChanged):
        # Ensure the message is coming from the correct directory widget
        # TODO: Could probably add a readonly flag to Directory to prevent having this check
        if self._update_preview_task and not self._update_preview_task.done():
            self._update_preview_task.cancel()

        if event.sender.id == "current-dir":
            if event.path.is_file():
                self._update_preview_task = asyncio.create_task(
                    self.show_syntax(event.path))
            elif event.path.is_dir():
                self.query_one("#preview", Preview).show_directory_preview(event.path)

    async def show_syntax(self, path: Path) -> None:
        async with aiofiles.open(path, mode='r') as f:
            print("READING")
            # TODO - if they start scrolling preview, load more than 1024 bytes.
            contents = await f.read(1024)
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
