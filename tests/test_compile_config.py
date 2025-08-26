import os
from functools import partial
from io import StringIO
from pathlib import Path
from textwrap import dedent

import hiyapyco
import pytest
import yaml
from click.testing import CliRunner
from ruamel.yaml import YAML

from dso._compile_config import (
    _get_list_of_configs_to_compile,
    _get_parent_configs,
    _load_yaml_with_auto_adjusting_paths,
)
from dso.cli import dso_compile_config


def _setup_yaml_configs(tmp_path, configs: dict[str, dict]):
    for path, dict_ in configs.items():
        path = tmp_path / path
        path.parent.mkdir(exist_ok=True, parents=True)
        with path.open("w", encoding="utf-8") as f:
            yaml.safe_dump(dict_, f)


@pytest.mark.parametrize("relative", [True, False])
@pytest.mark.parametrize("interpolate", [True, False])
def test_auto_adjusting_path(tmp_path, interpolate, relative):
    """Test that auto-adjusting paths work as expected.

    If `interpolate` is `True`, the AutoAdjustingPath object
    is already evaluated by hiyapyco, otherwise it is returned
    as an object that can be dumped by ruamel using the custom representer.
    """
    test_file = tmp_path / "params.in.yaml"
    (tmp_path / ".git").mkdir()
    destination = tmp_path / "subproject1" / "stageA"
    destination.mkdir(parents=True)
    (tmp_path / "test.txt").touch()  # create fake file, otherwise check for missing file will fail.

    with test_file.open("w", encoding="utf-8") as f:
        f.write(
            dedent(
                """\
                my_path: !path ./test.txt
                """
            )
        )

    with test_file.open("r", encoding="utf-8") as f:
        res = hiyapyco.load(
            str(test_file),
            method=hiyapyco.METHOD_MERGE,
            interpolate=interpolate,
            loader_callback=partial(
                _load_yaml_with_auto_adjusting_paths,
                destination=destination,
                missing_path_warnings=set(),
                relative=relative,
            ),
        )

    # Dump with ruamel then parse back to compare value cleanly
    ruamel = YAML()
    with StringIO() as s:
        ruamel.dump(res, s)
        actual_yaml = s.getvalue()

    loaded = yaml.safe_load(actual_yaml)
    assert "my_path" in loaded

    if relative:
        # Expected relative path from destination to source; OS-native separators
        expected_rel = os.path.normpath(os.path.join("..", "..", "test.txt"))
        assert loaded["my_path"] == expected_rel
    else:
        # Expected absolute path with OS-native separators
        expected_abs = str((tmp_path / "test.txt").resolve())
        assert loaded["my_path"] == expected_abs


@pytest.mark.parametrize("relative", [True, False])
@pytest.mark.parametrize(
    "test_yaml,expected_rel",
    [
        (
            """\
            A: !path dir_A
            B: "{{ A }}/B.txt"
            """,
            "dir_A/B.txt",
        ),
        (
            """\
            A: dir_A
            B: !path "{{ A }}/B.txt"
            """,
            "dir_A/B.txt",
        ),
    ],
)
def test_auto_adjusting_path_with_jinja(tmp_path, relative, test_yaml, expected_rel):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path) as td:
        td = Path(td)
        test_file = td / "params.in.yaml"
        (td / ".git").mkdir()

        # relative=True is default; when False, set config to produce absolute paths
        if not relative:
            (td / "pyproject.toml").write_text("[tool.dso]\nuse_relative_paths = false", encoding="utf-8")

        test_file.write_text(dedent(test_yaml), encoding="utf-8")

        result = runner.invoke(dso_compile_config, [])
        print(result.output)
        assert result.exit_code == 0

        with (td / "params.yaml").open(encoding="utf-8") as f:
            compiled = yaml.safe_load(f)
            assert "B" in compiled
            if relative:
                # Expect OS-native separators
                expected = os.path.normpath(expected_rel)
                assert compiled["B"] == expected
            else:
                # Expect absolute path under target directory (OS-native separators)
                expected_abs = str((td / expected_rel).resolve())
                assert compiled["B"] == expected_abs


def test_compile_configs(tmp_path):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path) as td:
        td = Path(td)
        (td / ".git").mkdir()
        _setup_yaml_configs(
            td,
            {
                "params.in.yaml": {"only_root": "foo", "value": "root", "list": [1, 2, 3]},
                "A/B/params.in.yaml": {"value": "B", "list": [3, 4]},
                "A/B/C/params.in.yaml": {"value": "C", "jinja2": "{{ only_root }}", "list": [5]},
            },
        )
        result = runner.invoke(dso_compile_config, [])
        print(result.output)
        assert result.exit_code == 0
        with (td / "params.yaml").open(encoding="utf-8") as f:
            assert yaml.safe_load(f) == {"only_root": "foo", "value": "root", "list": [1, 2, 3]}
        with (td / "A/B/params.yaml").open(encoding="utf-8") as f:
            assert yaml.safe_load(f) == {"only_root": "foo", "value": "B", "list": [1, 2, 3, 4]}
        with (td / "A/B/C/params.yaml").open(encoding="utf-8") as f:
            assert yaml.safe_load(f) == {"only_root": "foo", "value": "C", "list": [1, 2, 3, 4, 5], "jinja2": "foo"}


def test_compile_configs_null_override(tmp_path):
    """Test that null overrides any value"""
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path) as td:
        td = Path(td)
        (td / ".git").mkdir()
        _setup_yaml_configs(
            td,
            {
                "params.in.yaml": {"str": "str", "list": [1, 2, 3], "dict": {"A": 1, "B": 2}, "null": None},
                "A/B/params.in.yaml": {"str": None, "list": None, "dict": None, "null": None},
            },
        )
        result = runner.invoke(dso_compile_config, [])
        print(result.output)
        assert result.exit_code == 0
        with (td / "params.yaml").open(encoding="utf-8") as f:
            assert yaml.safe_load(f) == {"str": "str", "list": [1, 2, 3], "dict": {"A": 1, "B": 2}, "null": None}
        with (td / "A/B/params.yaml").open(encoding="utf-8") as f:
            assert yaml.safe_load(f) == {"str": None, "list": None, "dict": None, "null": None}


@pytest.mark.parametrize(
    "current_config,expected",
    [
        ["params.in.yaml", ["params.in.yaml"]],
        ["A/B/C/params.in.yaml", ["params.in.yaml", "A/B/params.in.yaml", "A/B/C/params.in.yaml"]],
        ["D/params.in.yaml", ["params.in.yaml", "D/params.in.yaml"]],
        ["E/params.in.yaml", ["params.in.yaml", "E/params.in.yaml"]],
    ],
)
def test_get_parent_configs(tmp_path, current_config, expected):
    current_config = tmp_path / current_config
    expected = [tmp_path / x for x in expected]
    all_configs = {
        tmp_path / x
        for x in [
            "params.in.yaml",
            "A/B/params.in.yaml",
            "A/B/C/params.in.yaml",
            "D/params.in.yaml",
            "E/params.in.yaml",
            "E/F/params.in.yaml",
        ]
    }

    res = _get_parent_configs(current_config, all_configs)
    assert res == expected


@pytest.mark.parametrize(
    "paths,expected",
    [
        [
            ["."],
            [
                "params.in.yaml",
                "A/B/params.in.yaml",
                "A/B/C/params.in.yaml",
                "D/params.in.yaml",
                "E/params.in.yaml",
                "E/F/params.in.yaml",
            ],
        ],
        [
            ["A"],
            [
                "params.in.yaml",
                "A/B/params.in.yaml",
                "A/B/C/params.in.yaml",
            ],
        ],
        [
            ["E"],
            [
                "params.in.yaml",
                "E/params.in.yaml",
                "E/F/params.in.yaml",
            ],
        ],
        [
            ["E/F"],
            [
                "params.in.yaml",
                "E/params.in.yaml",
                "E/F/params.in.yaml",
            ],
        ],
        [
            ["A", "E/F/"],
            [
                "params.in.yaml",
                "A/B/params.in.yaml",
                "A/B/C/params.in.yaml",
                "E/params.in.yaml",
                "E/F/params.in.yaml",
            ],
        ],
        # test that parents are also compiled if no params.in.yaml is in the selected directory.
        [["E/G/"], ["params.in.yaml", "E/params.in.yaml"]],
    ],
)
def test_get_list_of_configs_to_compile(tmp_path, paths, expected):
    # pretend this is a git repo
    (tmp_path / ".git").mkdir()
    # create mock directory structure
    for x in [
        "params.in.yaml",
        "A/B/params.in.yaml",
        "A/B/C/params.in.yaml",
        "D/params.in.yaml",
        "E/params.in.yaml",
        "E/F/params.in.yaml",
        "E/G/test.qmd",
    ]:
        (tmp_path / x).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / x).touch()

    expected = [tmp_path / x for x in expected]
    paths = [tmp_path / x for x in paths]

    res = _get_list_of_configs_to_compile(paths, tmp_path)
    assert sorted(res) == sorted(expected)
