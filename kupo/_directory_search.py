from textual import events
from textual.app import ComposeResult
from textual.binding import Binding
from textual.widget import Widget
from textual.widgets import Input


class DirectorySearch(Widget):
    BINDINGS = [
        Binding("escape", "hide_search", "Cancel search", key_display="ESC"),
        Binding("enter", "select_current", "Select")
    ]

    def compose(self) -> ComposeResult:
        self.input = Input(placeholder="Type to filter this directory...",
                           id="directory-search-input")
        yield self.input

    def on_mount(self, event: events.Mount) -> None:
        from ._directory import Directory
        self.current_dir = self.app.query_one("#current-dir", Directory)

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.sender.id != "directory-search-input":
            return
        self.current_dir.filter = event.value
        warning_banner = self.app.query_one("#current-dir-filter-warning")
        warning_banner.display = False

    def action_hide_search(self):
        self.display = False
        self.current_dir.focus()

    def key_up(self, event: events.Key):
        self.current_dir.selected_index -= 1

    def key_down(self, event: events.Key):
        self.current_dir.selected_index += 1

    def key_enter(self, event: events.Key):
        self.current_dir.goto_selected_path()

    def focus(self, scroll_visible: bool = True) -> None:
        self.query_one("#directory-search-input").focus()
        warning_banner = self.app.query_one("#current-dir-filter-warning")
        warning_banner.display = False
