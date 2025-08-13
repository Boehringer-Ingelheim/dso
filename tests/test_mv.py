from os import chdir
from subprocess import check_call

import pytest
from click.testing import CliRunner

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


def test_mv_stage_with_dependencies(dso_project_with_multiple_stages):
    runner = CliRunner()
    project_dir = dso_project_with_multiple_stages.resolve()
    source = "01_Preprocessing"
    target = "10_Preprocessing"
    source_dir = project_dir / "0200_AnalysisA" / source
    target_dir = project_dir / "0200_AnalysisA" / target

    result = runner.invoke(
        dso_mv,
        [
            str(source_dir),
            str(target_dir),
        ],
    )
    print(result.output)
    assert result.exit_code == 0
    assert (target_dir).is_dir()
    assert (project_dir / "params.in.yaml").is_file()
    assert f'"{target_dir}":' in (project_dir / "params.in.yaml").read_text()
    assert f'"{source_dir}":' not in (project_dir / "params.in.yaml").read_text()
