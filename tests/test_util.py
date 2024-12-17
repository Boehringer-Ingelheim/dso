import pytest

from dso._util import _find_in_parent, _git_list_files, _read_dot_dso_json, _update_dot_dso_json


@pytest.mark.parametrize(
    "file_or_folder,recurse_barrier,expected",
    [
        [".git", None, ".git"],
        ["params.in.yaml", None, "A/params.in.yaml"],
        ["doesntexist", None, None],
        [".git", "A/B", None],
        [".git", ".", ".git"],
        ["params.in.yaml", "A", "A/params.in.yaml"],
    ],
)
def test_find_in_parent(tmp_path, file_or_folder, recurse_barrier, expected):
    subfolder = tmp_path / "A/B/C/D"
    subfolder.mkdir(parents=True)
    (tmp_path / ".git").mkdir()
    (tmp_path / "A" / "params.in.yaml").touch()
    (tmp_path / "params.in.yaml").touch()
    if expected is not None:
        expected = tmp_path / expected
    if recurse_barrier is not None:
        recurse_barrier = tmp_path / recurse_barrier
    assert _find_in_parent(subfolder, file_or_folder, recurse_barrier) == expected


def test_dot_dso_json(dso_project):
    config = _read_dot_dso_json(dso_project)
    assert config == {}
    _update_dot_dso_json(dso_project, {"foo": "bar"})
    config = _read_dot_dso_json(dso_project)
    assert config["foo"] == "bar"
    _update_dot_dso_json(dso_project, {"xxx": "yyy"})
    config = _read_dot_dso_json(dso_project)
    assert config["foo"] == "bar"
    assert config["xxx"] == "yyy"
    _update_dot_dso_json(dso_project, {"xxx": "zzz"})
    config = _read_dot_dso_json(dso_project)
    assert config["foo"] == "bar"
    assert config["xxx"] == "zzz"


def test_git_list_files(dso_project):
    files = _git_list_files(dso_project)
    assert files == [
        dso_project / x
        for x in [
            ".dvc/.gitignore",
            ".dvc/config",
            ".dvcignore",
            ".editorconfig",
            ".gitattributes",
            ".gitignore",
            ".pre-commit-config.yaml",
            "README.md",
            "dvc.yaml",
            "params.in.yaml",
            "pyproject.toml",
        ]
    ]
