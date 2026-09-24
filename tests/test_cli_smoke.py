"""T-P1-01 smoke tests: the package imports and the console entry point responds."""

from typer.testing import CliRunner

import sbr
from sbr.cli.app import app

runner = CliRunner()


def test_package_has_version() -> None:
    assert sbr.__version__


def test_help_lists_program() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Second Brain RAG" in result.output


def test_version_command() -> None:
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert result.output.strip() == sbr.__version__
