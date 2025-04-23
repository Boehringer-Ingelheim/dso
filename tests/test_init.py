from pathlib import Path
from shutil import rmtree
from subprocess import check_call

from click.testing import CliRunner

from dso.cli import dso_init


def test_init(tmp_path):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path) as td:
        result = runner.invoke(dso_init, ["testproject", "--description", "testdescription"])
        print(result.output)
        td = Path(td)
        assert result.exit_code == 0
        assert (td / "testproject").is_dir()
        assert (td / "testproject" / ".git").is_dir()
        assert "testdescription" in (td / "testproject" / "README.md").read_text()
        # Check that all pre-commit checks pass on the newly initiated template
        check_call(["pre-commit", "install"], cwd=td / "testproject")
        check_call(["pre-commit", "run", "--all-files"], cwd=td / "testproject")


def test_init_existing_dir(dso_project):
    runner = CliRunner()
    # delete some files
    (dso_project / "params.in.yaml").unlink()
    (dso_project / "README.md").unlink()
    rmtree(dso_project / ".git")

    result = runner.invoke(dso_init, [str(dso_project), "--description", "testdescription"], input="y")
    assert result.exit_code == 0
    assert (dso_project).is_dir()
    assert (dso_project / ".git").is_dir()
    assert "testdescription" in (dso_project / "README.md").read_text()

    # Check that all pre-commit checks pass on the newly initiated template
    check_call(["pre-commit", "install"], cwd=dso_project)
    check_call(["pre-commit", "run", "--all-files"], cwd=dso_project)
