from os import chdir
from textwrap import dedent

import pytest
from click.testing import CliRunner

from dso._get_config import _filter_nested_dict, get_config
from dso.cli import dso_get_config


@pytest.mark.parametrize(
    "data, keys, expected",
    [
        ({"xxx": {"yyy": 123}}, ["xxx.yyy"], {"xxx": {"yyy": 123}}),
        ({"xxx": {"yyy": 123, "zzz": 123}}, ["xxx", "xxx.zzz"], {"xxx": {"yyy": 123, "zzz": 123}}),
        ({"xxx": {"yyy": 123, "zzz": 123}, "aaa": "bbb"}, ["xxx.yyy"], {"xxx": {"yyy": 123}}),
        ({"xxx": {"yyy": {"zzz": 123}}}, ["xxx.yyy.zzz"], {"xxx": {"yyy": {"zzz": 123}}}),
        ({"xxx": 123, "yyy": 123}, ["xxx", "yyy"], {"xxx": 123, "yyy": 123}),
        ({"xxx": {"yyy": 123, "zzz": 123, "aaa": 123}}, ["xxx.yyy", "xxx.zzz"], {"xxx": {"yyy": 123, "zzz": 123}}),
        (
            {"xxx": {"yyy": {"zzz": 123, "aaa": 123}, "bbb": 123, "ccc": {"ddd": 123}}},
            ["xxx.yyy.zzz", "xxx.yyy.aaa"],
            {"xxx": {"yyy": {"zzz": 123, "aaa": 123}}},
        ),
    ],
)
def test_get_nested_dict(data, keys, expected):
    assert _filter_nested_dict(data, keys) == expected


def test_get_config(dso_project):
    chdir(dso_project)
    stage = dso_project / "mystage"
    stage.mkdir()
    (stage / "params.in.yaml").touch()

    (dso_project / "params.in.yaml").write_text(
        dedent(
            """\
            parent:
               foo: !path mystage/input/A.txt
               bar: !path mystage/input/B.txt
               baz: !path mystage/input/C.txt
            param: 42
            other: "rocket"
            """
        )
    )

    (stage / "dvc.yaml").write_text(
        dedent(
            """\
            stages:
               mystage01:
                 params:
                   - param
                 deps:
                   - ${ parent.foo }
                 outs:
                   - ${ parent.bar }
                 cmd: "echo Hello World!"
               mystage02:
                 params:
                   - parent.foo
                 deps:
                   - parent.bar
                   - ${ param }
                 cmd: ""
               mystage03:
                 deps:
                   - /some/path/${ parent.foo }/xxx/${other}
            """
        )
    )

    # raises an error because there are multiple stages
    with pytest.raises(SystemExit):
        get_config("mystage")

    assert get_config("mystage", all=True) == {
        "parent": {"foo": "input/A.txt", "bar": "input/B.txt", "baz": "input/C.txt"},
        "param": 42,
        "other": "rocket",
    }

    assert get_config("mystage:mystage01") == {"parent": {"foo": "input/A.txt", "bar": "input/B.txt"}, "param": 42}
    assert get_config("mystage:mystage02") == {"parent": {"foo": "input/A.txt"}, "param": 42}
    assert get_config("mystage:mystage03") == {"parent": {"foo": "input/A.txt"}, "other": "rocket"}


def test_get_config_order(dso_project):
    chdir(dso_project)
    stage = dso_project / "mystage"
    stage.mkdir()
    (stage / "params.in.yaml").touch()

    (dso_project / "params.in.yaml").write_text(
        dedent(
            """\
            B1:
               C: 5
               A: 42
               D: 600
               B: 20
               Z: 19
               X: 27
            A1:
              - C
              - B
              - A
              - Z
              - X
            Z1:
              ZZ1: 1
              ZZ7: 2
              ZZ3: 42
              ZZ2: 0
            X1: "bar"
            """
        )
    )

    (stage / "dvc.yaml").write_text(
        dedent(
            """\
            stages:
               mystage01:
                 params:
                   - B1
                   - Z1.ZZ3
                   - Z1.ZZ7
                   - A1
                   - X1
                 cmd: "echo Hello World!"
            """
        )
    )

    config = get_config("mystage")
    assert list(config) == ["B1", "A1", "Z1", "X1"]
    assert config["A1"] == ["C", "B", "A", "Z", "X"]
    assert list(config["Z1"]) == ["ZZ7", "ZZ3"]
    assert list(config["B1"]) == ["C", "A", "D", "B", "Z", "X"]


def test_get_config_matrix(dso_project):
    """Test that get-config is compatible with dvc's matrix feature"""
    chdir(dso_project)
    stage = dso_project / "mystage"
    stage.mkdir()
    (stage / "params.in.yaml").touch()

    (dso_project / "params.in.yaml").write_text(
        dedent(
            """\
            matrix_param: ['p1', 'p2']
            A: "aaa"
            B: "bbb"
            """
        )
    )

    (stage / "dvc.yaml").write_text(
        dedent(
            """\
            stages:
               mystage01:
                 matrix:
                    mp: ${ matrix_param }
                 params:
                   - A
                   - item.mp
                 outs:
                   - output/${ item.mp }
                 cmd: "echo Hello World!"
            """
        )
    )

    config = get_config("mystage")
    assert list(config) == ["A"]


def test_get_config_path_relative_to_root_dir(quarto_stage):
    chdir(quarto_stage)
    config1 = get_config("quarto_stage")

    chdir("..")
    config2 = get_config("quarto_stage")

    assert config1 == config2


def test_get_config_invalid_stage(dso_project):
    chdir(dso_project)
    with pytest.raises(SystemExit):
        get_config("doesntexist")


def test_get_config_cli(quarto_stage):
    runner = CliRunner()
    chdir(quarto_stage)
    result = runner.invoke(dso_get_config, ["quarto_stage"])
    assert result.exit_code == 0
    assert "quarto:" in result.output
