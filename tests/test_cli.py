from click.testing import CliRunner

from dso.cli import cli


def test_root_command():
    runner = CliRunner()
    result = runner.invoke(cli)
    assert result.exit_code == 0
