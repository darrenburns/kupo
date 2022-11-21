from __future__ import annotations

from pathlib import Path

from rich.syntax import Syntax
from textual.binding import Binding
from textual.widgets import Static

from kupo._directory import DirectoryListRenderable
from kupo._files import list_files_in_dir


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
        directory_style = self.get_component_rich_style("directory--dir")
        directory = DirectoryListRenderable(
            list_files_in_dir(path),
            selected_index=None,
            dir_style=directory_style,
            meta_column_style=self.get_component_rich_style("directory--meta-column"),
        )
        self.update(directory)

    def action_up(self):
        self.parent.scroll_up(animate=False)

    def action_down(self):
        # TODO: This condition is a hack to workaround Textual seemingly scrolling
        #  1 more than it should, even when no vertical scrollbar.
        if not isinstance(self.renderable, DirectoryListRenderable):
            self.parent.scroll_down(animate=False)

    def action_top(self):
        self.parent.scroll_home(animate=False)

    def action_bottom(self):
        self.parent.scroll_end(animate=False)
