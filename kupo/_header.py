from __future__ import annotations

import getpass
import os
import socket

from rich.console import RenderableType
from rich.text import Text
from textual.app import ComposeResult
from textual.reactive import reactive
from textual.widget import Widget


class HeaderCurrentPath(Widget):
    path = reactive(None, layout=True)

    def render(self) -> RenderableType:
        if not self.path:
            return ""

        path = str(self.path.name)
        root = str(self.path.parent) + os.path.sep
        return Text.assemble((root, "dim"), (path, "bold"))


class HeaderHost(Widget):
    def render(self) -> RenderableType:
        return "[dim]@[/]" + socket.gethostname()


class HeaderUser(Widget):
    def render(self) -> RenderableType:
        return getpass.getuser()


class Header(Widget):
    def __init__(
        self,
        *,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ):
        super().__init__(name=name, id=id, classes=classes)

    def compose(self) -> ComposeResult:
        yield HeaderUser(id="header-user")
        yield HeaderHost(id="header-host")
        yield HeaderCurrentPath(id="header-current-path")
