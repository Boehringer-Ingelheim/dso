import os
from os import chdir

import pytest
from click.testing import CliRunner

from dso.cli import dso_exec


@pytest.mark.parametrize("quiet", [None, "2"])
@pytest.mark.parametrize("launch_dir", ["project_root", "stage"])
def test_exec_quarto(quarto_stage, quiet, launch_dir):
    runner = CliRunner()
    if launch_dir == "project_root":
        chdir(quarto_stage / "..")
        stage_path = quarto_stage.name
    else:
        chdir(quarto_stage)
        stage_path = "."

    if quiet is not None:
        os.environ["DSO_QUIET"] = quiet

    result = runner.invoke(dso_exec, ["quarto", stage_path])
    assert result.exit_code == 0
    assert (quarto_stage / "report" / "quarto_stage.html").is_file()
    assert (quarto_stage / "output" / "hello.txt").is_file()
    assert "Hello World!" in (quarto_stage / "report" / "quarto_stage.html").read_text()


def test_exec_quarto_empty_params(quarto_stage_empty_configs):
    runner = CliRunner()
    chdir(quarto_stage_empty_configs)
    stage_path = "."

    result = runner.invoke(dso_exec, ["quarto", stage_path])
    assert result.exit_code == 0
    assert (quarto_stage_empty_configs / "report" / "quarto_stage.html").is_file()
    assert "Hello World!" in (quarto_stage_empty_configs / "report" / "quarto_stage.html").read_text()


def test_exec_quarto_bibliography(quarto_stage_bibliography):
    runner = CliRunner()
    chdir(quarto_stage_bibliography)
    stage_path = "."

    result = runner.invoke(dso_exec, ["quarto", stage_path])
    assert result.exit_code == 0
    assert (quarto_stage_bibliography / "report" / "quarto_stage.html").is_file()
    assert "Knuth" in (quarto_stage_bibliography / "report" / "quarto_stage.html").read_text()


def test_exec_quarto_stylesheet(quarto_stage_css):
    runner = CliRunner()
    chdir(quarto_stage_css)
    stage_path = "."

    result = runner.invoke(dso_exec, ["quarto", stage_path])
    assert result.exit_code == 0
    assert (quarto_stage_css / "report" / "quarto_stage.html").is_file()
    assert "h2.veryspecialclass1" in (quarto_stage_css / "report" / "quarto_stage.html").read_text()
    assert "h2.veryspecialclass2" in (quarto_stage_css / "report" / "quarto_stage.html").read_text()
