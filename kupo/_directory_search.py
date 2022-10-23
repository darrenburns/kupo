from textual.app import ComposeResult
from textual.binding import Binding
from textual.widget import Widget
from textual.widgets import Input


class DirectorySearch(Widget):
    BINDINGS = [
        Binding("escape", "hide_search", "Cancel search", key_display="esc")
    ]

    def compose(self) -> ComposeResult:
        yield Input(placeholder="Type to filter this directory...",
                    id="directory-search-input")

    def action_hide_search(self):
        self.display = False
        self.app.query_one("#current-dir").focus()

    def focus(self, scroll_visible: bool = True) -> None:
        self.query_one("#directory-search-input").focus()
