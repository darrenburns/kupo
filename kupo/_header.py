from __future__ import annotations

from rich.console import RenderableType
from textual.app import ComposeResult
from textual.widget import Widget


class HeaderTitle(Widget):
    def render(self) -> RenderableType:
        return " ⌒ ● ⌒ "


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
        yield HeaderTitle()
