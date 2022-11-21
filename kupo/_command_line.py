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

from kupo._argparse import KupoArgParser, ParsingError
from kupo._directory import Directory

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

        print(f"command is {command!r}")
        if Command.is_valid_command(command):
            reference.display = True
            reference.command_name = command
        else:
            reference.display = False

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.sender.id != "command-line-input":
            return

        # # TODO: Add the command to our history (we could save to disk too)
        input = event.value

        args = shlex.split(input, posix=not WINDOWS)
        if not args:
            return
        elif len(args) == 1:
            command_name = args[0]
        else:
            command_name = args[0]
            args = args[1:]

        # # TODO We should look up the correct argument parser based on command,
        # #  for now we'll just hardcode until there are more commands.

        command = Command.load_command(command_name)
        if not command:
            return

        command.run(cmd_line=self, args=args)

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
class Command:
    command: str = ""
    syntax: str = ""
    description: str = ""

    @classmethod
    def load_command(cls, command_string: str) -> "Command | None":
        return _COMMANDS.get(command_string)

    @classmethod
    def is_valid_command(cls, command: str) -> bool:
        return command in _COMMANDS

    @property
    def arg_parser(self) -> KupoArgParser:
        raise NotImplementedError

    def run(self, cmd_line: CommandLine, args: list[str]) -> None:
        raise NotImplementedError


@dataclass
class Cd(Command):
    command: str = "cd",
    syntax: str = "[b]cd[/] [i]PATH[/]"
    description: str = "Go to the directory at [i]PATH[/]."

    @property
    def arg_parser(self) -> KupoArgParser:
        parser = KupoArgParser()
        parser.add_argument("path", type=Path)
        return parser

    def run(self, cmd_line: CommandLine, args: list[str]) -> None:
        parser = self.arg_parser

        try:
            parsed_args = parser.parse_args(args)
        except ParsingError:
            # TODO: indicate error somehow
            print("WOOPS, couldn't parse that.")
            return

        path = parsed_args.path
        if not path:
            return

        path: Path = path.expanduser()
        current_directory: Path = cmd_line.app.query_one("#current-dir", Directory).path
        path = current_directory.joinpath(path)
        if path.is_dir():
            target_path = path
            cmd_line.emit_no_wait(
                Directory.CurrentDirChanged(
                    cmd_line, new_dir=target_path, from_dir=None
                )
            )
            cmd_line.query_one("#command-line-input", Input).value = ""


_COMMANDS: dict[str, Command] = {
    "cd": Cd(),
}


class CommandReference(Widget):
    command_name = reactive("", layout=True)

    def render(self) -> RenderableType:
        print(f"getting {self.command_name}")
        info = _COMMANDS.get(self.command_name, None)
        if not info:
            return ""

        print(info.syntax)
        return Text.assemble(
            Text.from_markup(info.syntax),
            (" ╲╲╲ ", "green"),
            Text.from_markup(info.description),
        )
