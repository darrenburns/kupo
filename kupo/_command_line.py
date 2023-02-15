from __future__ import annotations

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

    selection_count = reactive(0)

    def compose(self) -> ComposeResult:
        yield Horizontal(
            Static(" ❯❯❯ ", id="command-line-prompt"),
            Input(placeholder="Enter a command", id="command-line-input"),
            Static(id="selection-info"),
            id="command-line-container"
        )

    def watch_selection_count(self, new_count: int) -> None:
        selection_info = self.query_one("#selection-info", Static)
        selection_info.display = new_count > 0
        selection_info.update(f"{self.selection_count} files selected")

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
        self.query_one("#command-line-input", Input).value = ""
        self.app.query_one("#current-dir", Directory).refresh()

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
        return KupoArgParser()

    def run(self, cmd_line: CommandLine, args: list[str]) -> None:
        raise NotImplementedError


@dataclass
class ChangeDirectory(Command):
    command: str = "cd"
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
            cmd_line.post_message_no_wait(
                Directory.CurrentDirChanged(
                    cmd_line, new_dir=target_path, from_dir=None
                )
            )


@dataclass
class MakeDirectory(Command):
    command: str = "mkdir"
    syntax: str = "[b]mkdir[/] [i]PATH[/]"
    description: str = "Create a directory at PATH"

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

        current_dir = cmd_line.app.query_one("#current-dir", Directory)
        current_path = current_dir.path
        path = path.expanduser()
        new_path = current_path.joinpath(path)
        # TODO: Generic means of confirmation.
        Path.mkdir(new_path)
        current_dir.update_source_directory(new_path.parent.resolve())

        # TODO: When we add support for parent=True, we'll need to ensure
        #  we pass the first part of the path arg to select_path, not the full
        #  thing?
        current_dir.select_path(new_path)
        current_dir.focus()


@dataclass
class Quit(Command):
    command: str = "quit"
    syntax: str = "[b]quit[/]"
    description: str = "Quit this app."

    def run(self, cmd_line: CommandLine, args: list[str]) -> None:
        cmd_line.app.exit()


@dataclass
class Touch(Command):
    command: str = "touch"
    syntax: str = "[b]touch[/] PATH"
    description: str = "Create an empty file at PATH."

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

        current_dir = cmd_line.app.query_one("#current-dir", Directory)
        current_path = current_dir.path

        given_path = parsed_args.path.expanduser()
        given_path = current_path.joinpath(given_path)
        Path.touch(given_path)

        current_dir.update_source_directory(given_path.parent.resolve())

        current_dir.select_path(given_path)
        current_dir.focus()

# TODO: __init_subclass__ is probably better than manually maintaining this:
_COMMANDS: dict[str, Command] = {
    "cd": ChangeDirectory(),
    "mkdir": MakeDirectory(),
    "q": Quit(),
    "quit": Quit(),
    "touch": Touch(),
}


class CommandReference(Widget):
    command_name = reactive("", layout=True)

    def render(self) -> RenderableType:
        print(f"getting {self.command_name}")
        info = _COMMANDS.get(self.command_name, None)
        print(info)
        if not info:
            return ""

        print(info.syntax)
        return Text.assemble(
            Text.from_markup(info.syntax),
            (" ╲ ", "green"),
            Text.from_markup(info.description),
        )
