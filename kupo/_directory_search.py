from textual.app import ComposeResult
from textual.binding import Binding
from textual.widget import Widget
from textual.widgets import Input


class DirectorySearch(Widget):
    BINDINGS = [
        Binding("escape", "hide_search", "Cancel search", key_display="ESC")
    ]

    def compose(self) -> ComposeResult:
        self.input = Input(placeholder="Type to filter this directory...",
                           id="directory-search-input")
        yield self.input

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.sender.id != "directory-search-input":
            return
        self.app.query_one("#current-dir").filter = event.value
        warning_banner = self.app.query_one("#current-dir-filter-warning")
        warning_banner.display = False

    def action_hide_search(self):
        self.display = False
        self.app.query_one("#current-dir").focus()

    def focus(self, scroll_visible: bool = True) -> None:
        self.query_one("#directory-search-input").focus()
        warning_banner = self.app.query_one("#current-dir-filter-warning")
        warning_banner.display = False
