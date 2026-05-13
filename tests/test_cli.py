from click.testing import CliRunner

from dso.cli import dso


def test_root_command():
    runner = CliRunner()
    result = runner.invoke(dso)
    assert result.exit_code == 0
