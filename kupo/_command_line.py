import platform
import shlex
from dataclasses import dataclass
from pathlib import Path

from rich.console import RenderableType
from rich.text import Text
from textual import events
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Static, Input

from _argparse import KupoArgParser, ParsingError
from _directory import Directory

PLATFORM = platform.system()
WINDOWS = PLATFORM == "Windows"


class CommandLine(Widget):
    BINDINGS = [
        Binding("escape", "cancel", "Cancel", key_display="ESC"),
    ]

    def compose(self) -> ComposeResult:
        yield Horizontal(
            Static(" ❯❯❯ ", id="command-line-prompt"),
            Input(placeholder="Enter a command", id="command-line-input"),
            id="command-line-container"
        )

    def on_input_changed(self, event: Input.Changed) -> None:
        reference = self.app.query_one("#command-reference", CommandReference)
        if event.input == "":
            reference.display = False
            return

        split = shlex.split(event.value, posix=not WINDOWS)
        if split:
            command, args = split[0], split[1:]
        else:
            reference.display = False
            return

        if reference.is_valid_command(command):
            reference.display = True
            reference.command = command
        else:
            reference.display = False

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.sender.id != "command-line-input":
            return

        # # TODO: Add the command to our history (we could save to disk too)
        input = event.value

        command, args = shlex.split(input, posix=not WINDOWS)
        print(command)
        print(args)

        # if split_index == -1:
        #     command, args = input, ""
        # else:
        #     command, args = input[:split_index], input[split_index:].strip()

        # # TODO We should look up the correct argument parser based on command,
        # #  for now we'll just hardcode until there are more commands.
        parser = KupoArgParser()
        parser.add_argument("path", type=Path)
        try:
            parsed_args = parser.parse_args([args])
        except ParsingError:
            # TODO: indicate error somehow
            print("WOOPS, couldn't parse that.")
            return

        path: Path = parsed_args.path.expanduser()

        current_directory: Path = self.app.query_one("#current-dir", Directory).path
        print(f"current_directory = {current_directory}")
        print(f"argument = {path}")
        path = current_directory.joinpath(path)
        if path.is_dir():
            target_path = path
            print(f"cd-ing to {target_path}")
            self.emit_no_wait(
                Directory.CurrentDirChanged(
                    self, new_dir=target_path, from_dir=None
                )
            )
            self.query_one("#command-line-input", Input).value = ""

    def on_descendant_focus(self, event: events.DescendantFocus) -> None:
        self.query_one("#command-line-prompt").add_class("active-prompt")

    def on_descendant_blur(self, event: events.DescendantBlur) -> None:
        self.query_one("#command-line-prompt").remove_class("active-prompt")

    def action_cancel(self):
        self.app.query_one("#current-dir").focus()

    def watch_descendant_has_focus(self, value: bool) -> None:
        if not value:
            self.app.query_one("#command-reference").display = False


@dataclass
class CommandInfo:
    command: str
    syntax: str
    description: str


_COMMAND_REFERENCES: dict[str, CommandInfo] = {
    "cd": CommandInfo("cd", "[b]cd[/] [i]PATH[/]",
                      "Go to the directory at [i]PATH[/]."),
}


class CommandReference(Widget):
    command = reactive("")

    def is_valid_command(self, command: str) -> bool:
        return command in _COMMAND_REFERENCES

    def render(self) -> RenderableType:
        info = _COMMAND_REFERENCES.get(self.command, None)
        if not info:
            return ""
        return Text.assemble(
            Text.from_markup(info.syntax),
            (" ╲ ", "dim green"),
            Text.from_markup(info.description),
        )
