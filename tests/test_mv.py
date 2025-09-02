from os import chdir
from os.path import relpath
from pathlib import Path
from subprocess import check_call

import pytest
from click.testing import CliRunner

from dso._compile_config import compile_all_configs
from dso.cli import dso_mv


@pytest.mark.parametrize(
    "source,target",
    [
        ["quarto_stage", "renamed"],
    ],
)
def test_mv_stage(quarto_stage, source, target):
    runner = CliRunner()
    chdir(quarto_stage)
    source_dir = quarto_stage.resolve()
    base_dir = source_dir.parent
    renamed_dir = base_dir / target

    result = runner.invoke(
        dso_mv,
        [
            str(source_dir),
            str(renamed_dir),
        ],
    )
    print(result.output)
    assert result.exit_code == 0
    assert (renamed_dir).is_dir()
    assert (renamed_dir / "dvc.yaml").is_file()
    assert f'"{target}":' in (renamed_dir / "dvc.yaml").read_text()
    assert (renamed_dir / "src" / f"{target}.qmd").is_file()
    assert target in (renamed_dir / "README.md").read_text()

    # Check that all pre-commit checks pass on the renamed template
    check_call(["pre-commit", "install"], cwd=renamed_dir)
    check_call(["pre-commit", "run", "--all-files"], cwd=renamed_dir)


def assert_params_file_content(path, rel_to_source, rel_to_target, file, similar=""):
    """
    Helper function for checking params.in.yaml files

    Check if params.in.yaml file in 'path' contains stage with 'file' with path 'rel_to_target'
    and not 'rel_to_source' anymore. If 'similar' is not empty, check if the similar target
    is still intact in params.in.yaml. if 'rel_to_source' is empty, do not check - since this is
    the target directory itself.
    """
    params_file = path / "params.in.yaml"
    assert params_file.is_file()
    params_content = params_file.read_text()
    assert f"{rel_to_target}{file}" in params_content
    if rel_to_source != "":
        assert f" {rel_to_source}{file}" not in params_content
    if similar != "":
        assert f"{similar}" in params_content


@pytest.mark.parametrize(
    "rel_source,rel_target",
    [
        ["0200_AnalysisA/01_Preprocessing", "0200_AnalysisA/10_Preprocessing"],
        ["0200_AnalysisA/01_Preprocessing", "01_Preprocessing"],
        ["0200_AnalysisA/01_Preprocessing", "10_Preprocessing"],
        ["0200_AnalysisA/01_Preprocessing", "0300_AnalysisB/10_Preprocessing"],
    ],
)
def test_mv_stage_with_dependencies(dso_project_with_multiple_stages, rel_source, rel_target):
    runner = CliRunner()
    project_dir = dso_project_with_multiple_stages.resolve()
    rel_source = Path(rel_source)
    rel_target = Path(rel_target)

    source = rel_source.name
    target = rel_target.name

    dir_0100 = "0100_ETL"
    dir_0200 = "0200_AnalysisA"
    dir_0300 = "0300_AnalysisB"
    path_source = project_dir / rel_source
    path_target = project_dir / rel_target
    path_0100 = project_dir / dir_0100
    path_0200 = project_dir / dir_0200
    path_0300 = project_dir / dir_0300

    similar = "01_Preprocessing/input/G.txt"
    path_similar = path_0300 / similar
    rel_similar = f"{dir_0300}/{similar}"

    result = runner.invoke(
        dso_mv,
        [
            str(path_source),
            str(path_target),
        ],
    )

    compile_all_configs([project_dir])

    print(result.output)
    assert result.exit_code == 0
    # assert that similar directory to source directory
    # was not altered
    assert path_similar.is_file()

    # assert that target exists and that references have been updated
    assert path_target.is_dir()
    target_dvc_file = path_target / "dvc.yaml"
    assert f'"{target}":' in (target_dvc_file.read_text())

    # assert the correct paths from project dir
    assert_params_file_content(project_dir, rel_source, rel_target, "/input/C.txt", rel_similar)

    # assert correct paths starting from path 0200
    assert_params_file_content(path_0200, source, target, "/input/C.txt", f"../{rel_similar}")

    # assert correct paths starting from target path
    assert_params_file_content(path_target, "", "", "input/C.txt", f"../../{rel_similar}")

    # assert correct paths from 0100
    assert_params_file_content(
        path_0100,
        f"../{rel_source}",
        f"../{rel_target}",
        "/input/C.txt",
        f"../{rel_similar}",
    )

    # assert correct paths from 0300 - directory containing the similar dir
    assert_params_file_content(
        path_0300,
        f"../{rel_source}",
        relpath(path_target, start=path_0300),
        "/input/C.txt",
        similar,
    )


def test_mv_stage_existing_dir(dso_project_with_multiple_stages):
    runner = CliRunner()
    project_dir = dso_project_with_multiple_stages.resolve()
    path_source = project_dir / "0200_AnalysisA" / "01_Preprocessing"
    path_target = project_dir / "0200_AnalysisA" / "02_Analysis"

    result = runner.invoke(
        dso_mv,
        [
            str(path_source),
            str(path_target),
        ],
    )

    assert result.exit_code == 1
    assert path_source.is_dir()
