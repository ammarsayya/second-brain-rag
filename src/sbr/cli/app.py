"""Typer application for the ``sbr`` command."""

from __future__ import annotations

import typer

from sbr import __version__

app = typer.Typer(
    name="sbr",
    help="Second Brain RAG: provenance-tracked knowledge system over read-only source corpora.",
    no_args_is_help=True,
    add_completion=False,
)


@app.callback()
def root() -> None:
    """Second Brain RAG command group."""


@app.command("version")
def version_cmd() -> None:
    """Print the sbr version."""
    typer.echo(__version__)


def main() -> None:
    """Console-script entry point."""
    app()
