from __future__ import annotations

from pathlib import Path

from rich.syntax import Syntax
from textual.geometry import Size
from textual.widgets import Static


class SyntaxPreview(Static):
    def __init__(
        self,
        *,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ):
        super().__init__(name=name, id=id, classes=classes)
        self._content_height = 0
        self._content_width = 0

    def update_content(self, text: str, path: Path) -> None:
        lines = text.split("\n")
        self._content_width = max(len(line) for line in lines)
        self._content_height = len(lines)
        lexer = Syntax.guess_lexer(str(path), text)
        self.update(Syntax(text, lexer))

    def get_content_height(self, container: Size, viewport: Size, width: int) -> int:
        return self._content_height

    def get_content_width(self, container: Size, viewport: Size) -> int:
        return self._content_width
