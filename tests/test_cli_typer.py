"""Typer-level tests via CliRunner: help output, completion wiring, exit
codes and the global --model option. Complements test_cli.py, which drives
main() directly."""
from typer.testing import CliRunner

from archi_tool.cli import app

runner = CliRunner()


def test_help_lists_all_commands():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for command in ("stats", "list", "show", "tree", "validate", "normalize",
                    "add-element", "add-relation", "set-property",
                    "remove-property", "move", "rename",
                    "set-documentation", "remove", "set-model-name", "render",
                    "slides", "add-view"):
        assert command in result.output


def test_completion_option_present():
    """Completion is a built-in Typer option. Assert it's registered rather
    than grepping help text, whose line wrapping depends on terminal width
    (Rich wraps under CI's narrow COLUMNS and splits the flag mid-string)."""
    import typer

    command = typer.main.get_command(app)
    option_names = {
        name for param in command.params for name in param.opts}
    assert "--install-completion" in option_names
    assert "--show-completion" in option_names


def test_no_args_shows_help_not_crash():
    result = runner.invoke(app, [])
    # no_args_is_help makes this a clean help exit, not an error
    assert "Usage:" in result.output


def test_unknown_command_is_usage_error(model_path):
    result = runner.invoke(app, ["--model", str(model_path), "bestaat-niet"])
    assert result.exit_code != 0


def test_global_model_option_before_subcommand(model_path):
    result = runner.invoke(app, ["--model", str(model_path), "validate"])
    assert result.exit_code == 0
    assert "OK: het model is consistent." in result.output


def test_missing_model_exit_code_one(tmp_path):
    result = runner.invoke(
        app, ["--model", str(tmp_path / "weg.archimate"), "validate"])
    assert result.exit_code == 1
    assert "Modelbestand niet gevonden" in result.output
