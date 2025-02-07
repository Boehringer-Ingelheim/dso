from os import chdir
from subprocess import check_call

import pytest
from click.testing import CliRunner

from dso.cli import dso_create


@pytest.mark.parametrize("template", ["bash", "quarto_r", "quarto_py", "quarto_ipynb"])
def test_create_stage(dso_project, template):
    runner = CliRunner()
    chdir(dso_project)
    result = runner.invoke(
        dso_create, ["stage", "teststage", "--template", template, "--description", "testdescription"]
    )
    print(result.output)
    assert result.exit_code == 0
    assert (dso_project / "teststage").is_dir()
    assert (dso_project / "teststage" / "dvc.yaml").is_file()
    assert "teststage:" in (dso_project / "teststage" / "dvc.yaml").read_text()
    if template == "quarto":
        assert (dso_project / "teststage" / "src" / "teststage.qmd").is_file()
        assert 'read_params("teststage")' in (dso_project / "teststage" / "src" / "teststage.qmd").read_text()
    assert "testdescription" in (dso_project / "teststage" / "README.md").read_text()
    # Check that all pre-commit checks pass on the newly initiated template
    check_call(["pre-commit", "install"], cwd=dso_project)
    check_call(["pre-commit", "run", "--all-files"], cwd=dso_project)


def test_create_folder(dso_project):
    runner = CliRunner()
    chdir(dso_project)
    result = runner.invoke(dso_create, ["folder", "testfolder"])
    print(result.output)
    assert result.exit_code == 0
    assert (dso_project / "testfolder").is_dir()
    assert (dso_project / "testfolder" / "dvc.yaml").is_file()
    assert (dso_project / "testfolder" / "params.in.yaml").is_file()
    # Check that all pre-commit checks pass on the newly initiated template
    check_call(["pre-commit", "install"], cwd=dso_project)
    check_call(["pre-commit", "run", "--all-files"], cwd=dso_project)


def test_create_folder_existing_dir(dso_project):
    """Test that dso create folder can be executed on an existing directory"""
    runner = CliRunner()
    (dso_project / "testfolder").mkdir()
    (dso_project / "testfolder" / "dvc.yaml").touch()
    chdir(dso_project)
    result = runner.invoke(dso_create, ["folder", "testfolder"], input="y")
    print(result.output)
    assert result.exit_code == 0
    assert (dso_project / "testfolder").is_dir()
    assert (dso_project / "testfolder" / "dvc.yaml").is_file()
    assert (dso_project / "testfolder" / "params.in.yaml").is_file()
    # Check that all pre-commit checks pass on the newly initiated template
    check_call(["pre-commit", "install"], cwd=dso_project)
    check_call(["pre-commit", "run", "--all-files"], cwd=dso_project)
