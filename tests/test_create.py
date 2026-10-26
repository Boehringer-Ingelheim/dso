import json
from os import chdir
from pathlib import Path
from subprocess import call, check_call

import pytest
from click.testing import CliRunner

from dso.cli import dso_create


@pytest.mark.parametrize("command", ["folder", "stage"])
def test_custom_template(command, tmp_path, dso_project):
    template_id = "test_template"
    lib_dir = tmp_path / "test_library"
    lib_dir.mkdir()
    template_dir = lib_dir / command / template_id
    template_dir.mkdir(parents=True)
    with (lib_dir / "index.json").open("w") as f:
        item = {
            "id": template_id,
            "description": "foobarstage",
            "usage": "...",
            "params": [
                {
                    "name": "name",
                    "description": "Stage/folder name",
                },
                {
                    "name": "description",
                    "description": "description",
                },
                {
                    "name": "custom_param",
                    "description": "A custom parameter",
                },
            ],
        }
        json.dump(
            {
                "id": "test_library2",
                "description": "foobar",
                "init": [],
                "folder": [item],
                "stage": [item],
            },
            f,
        )

    # add a test file that will be populated by jinja2 and is easy to verify
    with (template_dir / "test.json").open("w") as f:
        json.dump(
            {
                "name": "{{ name }}",
                "description": "{{ description }}",
                "custom_param": "{{ custom_param }}",
            },
            f,
        )

    runner = CliRunner()
    chdir(dso_project)

    result = runner.invoke(
        dso_create,
        [
            command,
            "testname",
            "--library",
            "test_library2",
            "--template",
            template_id,
            "--description",
            "testdescription",
            "--custom_param",
            "testcustom",
        ],
        env={"DSO_TEMPLATE_LIBRARIES": f"dso.templates:{lib_dir}"},
    )

    print(result.output)
    assert result.exit_code == 0

    with (dso_project / "testname" / "test.json").open("rb") as f:
        actual = json.load(f)

    assert actual == {
        "name": "testname",
        "description": "testdescription",
        "custom_param": "testcustom",
    }


@pytest.mark.parametrize("abspath", [True, False])
@pytest.mark.parametrize(
    "template,stage_path,expected_src",
    [
        ["bash", "teststage", None],
        ["quarto_r", "teststage", "src/teststage.qmd"],
        ["quarto_r", "subfolderA/teststage", "src/teststage.qmd"],
        ["quarto_py", "teststage", "src/teststage.qmd"],
        ["quarto_ipynb", "teststage", "src/teststage.ipynb"],
        ["quarto_jl", "teststage", "src/teststage.qmd"],
    ],
)
def test_create_stage(dso_project, template, stage_path, expected_src, abspath):
    """
    Test dso create stage

    Parameters
    ----------
    dso_project
        fixture with empty dso project
    template
        template name
    stage_path
        path/name of stage to be created
    expected_src
        expected path to created file in src folder, relative to stage_path
    abspath
        if True, convert stage_path to absolute before testing
    """
    runner = CliRunner()
    chdir(dso_project)
    result = runner.invoke(
        dso_create,
        [
            "stage",
            str((dso_project / stage_path).absolute() if abspath else stage_path),
            "--template",
            template,
            "--description",
            "testdescription",
        ],
    )
    print(result.output)
    assert result.exit_code == 0
    assert (dso_project / stage_path).is_dir()
    assert (dso_project / stage_path / "dvc.yaml").is_file()
    assert '"teststage":' in (dso_project / stage_path / "dvc.yaml").read_text()
    if expected_src is not None:
        assert (dso_project / stage_path / expected_src).is_file()
        # .replace to handle ipynb json
        assert f'read_params("{stage_path}")' in (dso_project / stage_path / expected_src).read_text().replace(
            '\\"', '"'
        )
    assert "testdescription" in (dso_project / stage_path / "README.md").read_text()
    # Check that all pre-commit checks pass on the newly initiated template
    check_call(["pre-commit", "install"], cwd=dso_project)
    check_call(["pre-commit", "run", "--all-files"], cwd=dso_project)


@pytest.mark.parametrize("template", ["bash", "quarto_r", "quarto_py", "quarto_ipynb", "quarto_jl"])
def test_create_stage_dvc_tracked_input(dso_project, template):
    """
    `.dvc` files in the `input` folder of a stage must be discoverable by DVC.

    DVC skips directories that its git backend (dulwich) reports as ignored when collecting `.dvc` files.
    dulwich matched `/input/*` against the `input/` directory itself, so `dvc pull`/`dvc push` without
    explicit targets silently skipped all `.dvc` files in `input/`.
    """
    from dvc.repo import Repo

    from dso._compile_config import compile_all_configs

    runner = CliRunner()
    chdir(dso_project)
    result = runner.invoke(
        dso_create, ["stage", "teststage", "--template", template, "--description", "testdescription"]
    )
    print(result.output)
    assert result.exit_code == 0

    input_dir = dso_project / "teststage" / "input"
    input_dir.mkdir(exist_ok=True)
    (input_dir / "data.txt").write_text("foo\n")
    (input_dir / "untracked.txt").write_text("bar\n")
    compile_all_configs([dso_project])

    with Repo(dso_project) as repo:
        repo.add(str(input_dir / "data.txt"))
    with Repo(dso_project) as repo:
        dvc_files = {Path(stage.path).relative_to(dso_project) for stage in repo.index.stages}
    assert Path("teststage/input/data.txt.dvc") in dvc_files

    # git must still ignore input data, but not the `.dvc` files
    assert call(["git", "check-ignore", "-q", "teststage/input/untracked.txt"], cwd=dso_project) == 0
    assert call(["git", "check-ignore", "-q", "teststage/input/data.txt.dvc"], cwd=dso_project) == 1


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
