from os import chdir
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


def test_mv_stage_with_dependencies(dso_project_with_multiple_stages):
    runner = CliRunner()
    project_dir = dso_project_with_multiple_stages.resolve()
    source = "01_Preprocessing"
    target = "10_Preprocessing"
    dir_0100 = "0100_ETL"
    dir_0200 = "0200_AnalysisA"
    dir_0300 = "0300_AnalysisB"
    path_source = project_dir / dir_0200 / source
    path_target = project_dir / dir_0200 / target
    path_0100 = project_dir / dir_0100
    path_0200 = project_dir / dir_0200
    path_0300 = project_dir / dir_0300
    rel_source = f"{dir_0200}/{source}"
    rel_target = f"{dir_0200}/{target}"
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
    assert path_target.is_dir()
    assert path_similar.is_file()
    target_dvc_file = path_target / "dvc.yaml"
    assert f'"{target}":' in (target_dvc_file.read_text())

    def assert_params_file_content(
        path, rel_to_source, rel_to_target, file, similar=""
    ):
        """
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

    assert_params_file_content(
        project_dir, rel_source, rel_target, "/input/C.txt", rel_similar
    )
    assert_params_file_content(
        path_0200, source, target, "/input/C.txt", f"../{rel_similar}"
    )
    assert_params_file_content(
        path_target, "", "", "input/C.txt", f"../../{rel_similar}"
    )
    assert_params_file_content(
        path_0100,
        f"../{rel_source}",
        f"../{rel_target}",
        "/input/C.txt",
        f"../{rel_similar}",
    )
    assert_params_file_content(
        path_0300, f"../{rel_source}", f"../{rel_target}", "/input/C.txt", similar
    )
