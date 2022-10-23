from textual import events
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.widget import Widget
from textual.widgets import Static, Input


class CommandLine(Widget):
    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
    ]

    def action_cancel(self):
        self.app.query_one("#current-dir").focus()

    def on_descendant_focus(self, event: events.DescendantFocus) -> None:
        self.query_one("#command-line-prompt").add_class("active-prompt")

    def on_descendant_blur(self, event: events.DescendantBlur) -> None:
        self.query_one("#command-line-prompt").remove_class("active-prompt")

    def compose(self) -> ComposeResult:
        yield Horizontal(
            Static(" ❯❯❯ ", id="command-line-prompt"),
            Input(placeholder="Enter a command", id="command-line-input"),
            id="command-line-container"
        )
