from __future__ import annotations

from argparse import ArgumentParser


class ParsingError(Exception):
    pass


class KupoArgParser(ArgumentParser):
    def error(self, message: str):
        pass

    def exit(self, status: int = ..., message: str | None = ...):
        pass
