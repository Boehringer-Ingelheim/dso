from __future__ import annotations

import importlib
import json
import subprocess
import sys
from collections.abc import Sequence
from contextlib import contextmanager
from functools import cache
from importlib import resources
from os import environ
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from rich.prompt import Confirm

from dso._logging import console, log

# compatibilty with python 3.10
try:
    import tomllib
except ImportError:
    import tomli as tomllib


if TYPE_CHECKING:
    from importlib.resources.abc import Traversable

DEFAULT_BRANCH = "master"


def check_project_roots(paths: Sequence[Path]) -> Path:
    """Check project roots for multiple paths and raise an error if they are ambiguous"""
    try:
        tmp_project_roots = {get_project_root(p) for p in paths}
    except FileNotFoundError:
        log.error("Not in a dso project (no .git directory found)")
        sys.exit(1)
    if len(tmp_project_roots) != 1:
        log.error("Specified paths point to an ambiguous project root.")
        sys.exit(1)
    return tmp_project_roots.pop()


def find_in_parent(start_directory: Path, file_or_folder: str, recurse_barrier: Path | None = None) -> Path | None:
    """
    Recursively walk up to the folder directory until we either find `file_or_folder` or reach the root.

    If recurse_barrier is specified, we don't recurse past this level.

    By using @cache this is efficient, even when called repeatedly.

    If the root is reached without finding the file, None is returned.
    """
    return _find_in_parent_abs(
        start_directory.absolute(),
        file_or_folder,
        recurse_barrier.absolute() if recurse_barrier is not None else None,
    )


@cache
def _find_in_parent_abs(start_directory: Path, file_or_folder: str, recurse_barrier: Path | None = None) -> Path | None:
    """
    Implementation of `_find_in_parent`, work only with absolute paths here.

    This is to ensure @cache doesn't lead to wrong results when calling this from different working directories.
    """
    if start_directory == Path("/"):
        return None
    if recurse_barrier is not None:
        if not start_directory.is_relative_to(recurse_barrier):
            return None
    if start_directory.is_file():
        return _find_in_parent_abs(start_directory.parent, file_or_folder, recurse_barrier)
    if (start_directory / file_or_folder).exists():
        return start_directory / file_or_folder
    else:
        return _find_in_parent_abs(start_directory.parent, file_or_folder, recurse_barrier)


def get_project_root(start_directory: Path) -> Path:
    """
    Find the dso project root.

    This is defined as the next parent directory that contains a `.git` directory.

    Parameters
    ----------
    start_directory : Path
        The directory to start the search from.

    Returns
    -------
    The project root

    Raises
    ------
    FileNotFoundError
        If the .git folder is not found.
    """
    proj_root = find_in_parent(start_directory, ".git")
    if proj_root is None:
        raise FileNotFoundError("Not within a dso project (No .git directory found)")
    else:
        # .parent, because proj_root points to the git directory
        return proj_root.parent


def get_template_path(template_type: Literal["init", "folder", "stage"], template_name: str) -> Traversable:
    template_module = importlib.import_module(f"dso.templates.{template_type}")
    return resources.files(template_module) / template_name


def _copy_with_render(source: Traversable, destination: Path, params: dict):
    """Fill all placeholders in a file with jinja2 and save file to destination"""
    from jinja2 import StrictUndefined, Template

    with source.open() as f:
        template = Template(f.read(), undefined=StrictUndefined)
    rendered_content = template.render(params)
    with destination.open("w") as file:
        file.write(rendered_content)
        # Non-empty files should have a terminal new-line to make the pre-commit hooks happy
        if len(rendered_content):
            file.write("\n")


def instantiate_template(template_path: Traversable, target_dir: Path | str, **params) -> None:
    """Copy a template folder to a target directory, filling all placeholder values."""
    from jinja2 import Template

    target_dir = Path(target_dir)

    def _traverse_template(curr_path, subdir):
        for p in curr_path.iterdir():
            if p.is_file():
                name_rendered = Template(p.name).render(params)
                # this file is used for checking in empty folders in git.
                if name_rendered != ".gitkeeptemplate":
                    target_file = target_dir / subdir / name_rendered
                    if not target_file.exists():
                        _copy_with_render(p, target_file, params)
            else:
                (target_dir / subdir / p.name).mkdir(exist_ok=True)
                _traverse_template(p, subdir / p.name)

    _traverse_template(template_path, Path("."))


def instantiate_with_repo(template: Traversable, target_dir: Path | str, **params) -> None:
    """Create a git repo in a directory and render a template inside.

    Creates an initial commit.
    """
    from git.repo import Repo

    target_dir = Path(target_dir)
    target_dir.mkdir(exist_ok=True)
    log.info("Created project directory.")

    instantiate_template(template, target_dir, **params)
    log.info("Created folder structure from template.")

    if not (target_dir / ".git").exists():
        Repo.init(target_dir)
        repo = Repo(target_dir)
        # set main as default branch
        repo.git.checkout("-b", DEFAULT_BRANCH)
        repo.git.symbolic_ref("HEAD", f"refs/heads/{DEFAULT_BRANCH}")
        repo.git.add(A=True)
        repo.index.commit("Initial commit generated by dso CLI tool.")
        log.info("Initalized local git repo.")


def git_list_files(dir: Path) -> list[Path]:
    """
    Recursively list all files in `dir` that are not .gitignored.

    This lists both files that are tracked and untracked by git.
    Source: https://stackoverflow.com/a/77197460/2340703
    """
    res = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=dir,
        capture_output=True,
    )
    if res.returncode:
        sys.exit(res.returncode)
    return [dir / Path(p) for p in res.stdout.decode("utf-8").strip().split("\n")]


@cache
def get_dso_config_from_pyproject_toml(dir: Path) -> dict:
    """
    Read the pyproject.toml file when within a project and return the [tool.dso] section as dict

    If the pyproject.toml file doesn't exist, or it doesn't have a [tool.dso] section,
    an empty dictionary is returned
    """
    project_root = get_project_root(dir)
    pyproject_toml = project_root / "pyproject.toml"
    if not pyproject_toml.exists():
        return {}
    with pyproject_toml.open("rb") as f:
        data = tomllib.load(f)
    return data.get("tool", {}).get("dso", {})


def _read_dot_dso_json(dir: Path):
    """
    Read .dso.json from the project directory

    The `.dso.json` file is file that can store project-specific settings and data generated by the dso CLI.
    It is not intended to be edited by the user.

    If the file doesn not exist it just means that is has not been generated yet. We return an empty dict in such a case.
    """
    project_root = get_project_root(dir)
    dot_dso_json = project_root / ".dso.json"
    if (dot_dso_json).exists():
        with dot_dso_json.open("rb") as f:
            return json.load(f)
    else:
        return {}


def _update_dot_dso_json(dir: Path, update_dict: dict):
    """
    Update the .dso.json with `update_dict`.

    Only keys present in `update_dict` will be updated. All other keys will be left as they are.
    """
    project_root = get_project_root(dir)
    dot_dso_json = project_root / ".dso.json"
    config = _read_dot_dso_json(dir)
    config.update(update_dict)

    with dot_dso_json.open("w") as f:
        json.dump(config, f)


@contextmanager
def add_directory(dir: Path):
    """Context manager that temporarily creates a directory and removes it again if it's empty"""
    dir.mkdir(exist_ok=True)
    try:
        yield
    finally:
        try:
            dir.rmdir()
        except OSError:
            # directory not empty
            pass


def check_ask_pre_commit(dir: Path):
    """
    Check if pre-commit hooks are installed and asks to install them

    If the user declines, info will be written to `.dso.json` to not ask again in the future.

    Additionally, we respect a `DSO_SKIP_CHECK_ASK_PRE_COMMIT` environment variable. If it is set
    to anything that evaluates as `True`, we skip the check and question altogether. This was a
    requirement introduced by the R API package: https://github.com/Boehringer-Ingelheim/dso/issues/50.
    """
    if environ.get("DSO_SKIP_CHECK_ASK_PRE_COMMIT", None):
        return
    config = _read_dot_dso_json(dir)
    if config.get("check_ask_pre_commit", True):
        project_root = get_project_root(dir)
        hook = project_root / ".git" / "hooks" / "pre-commit"
        if not hook.is_file() or "pre-commit" not in hook.read_text():
            console.print("Pre-commit hooks are not installed in this project.")
            console.print(
                "This hooks will take care of running consistency checks and automatically syncing [bold]dvc."
            )
            if Confirm.ask("[bold]Do you want to install the pre-commit hooks now?"):
                res = subprocess.run(["pre-commit", "install"], cwd=project_root)
                if res.returncode:
                    log.error("Failed to install pre-commit hooks")
                    sys.exit(res.returncode)
                else:
                    log.info("Pre-commit hooks installed successfully")
            else:
                _update_dot_dso_json(dir, {"check_ask_pre_commit": False})
