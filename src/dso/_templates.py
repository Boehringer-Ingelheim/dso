"""Helper functions for instantiating project/folder/stage templates"""

from __future__ import annotations

import importlib
import json
import os
import sys
from importlib import resources
from pathlib import Path
from textwrap import dedent
from typing import TYPE_CHECKING, Literal

from dso._logging import log

if TYPE_CHECKING:
    from importlib.resources.abc import Traversable

DEFAULT_BRANCH = "master"

# Minimal set of binary extensions we should not open as text / render
_BINARY_EXTS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".bmp",
    ".tiff",
    ".ico",
    ".pdf",
    ".zip",
    ".gz",
    ".bz2",
    ".xz",
    ".7z",
    ".dll",
    ".so",
    ".dylib",
    ".woff",
    ".woff2",
    ".ttf",
    ".otf",
}


def _split_template_libraries_env(raw: str) -> list[str]:
    """
    Split DSO_TEMPLATE_LIBRARIES into paths/modules.
    - If os.pathsep is present, split on that.
    - Otherwise split on ':' but keep Windows drive specifiers like 'C:\'.
    """
    if not raw:
        return []

    # If user used os.pathsep explicitly, just use it.
    if os.pathsep in raw:
        return [p for p in raw.split(os.pathsep) if p]

    # Fallback: smart ':' split that preserves 'X:\' on Windows
    parts: list[str] = []
    start = 0
    buf: list[str] = []
    i = 0
    while i < len(raw):
        ch = raw[i]
        if ch == ":":
            if os.name == "nt":
                # Drive colon (e.g., 'C:\') occurs at index 1 of a token and
                # is followed by a slash or backslash.
                if i == start + 1 and raw[start].isalpha() and i + 1 < len(raw) and raw[i + 1] in ("\\", "/"):
                    buf.append(":")
                    i += 1
                    continue
            # separator between libraries
            parts.append("".join(buf))
            buf = []
            start = i + 1
        else:
            buf.append(ch)
        i += 1
    parts.append("".join(buf))
    return [p for p in parts if p]


def _get_template_libraries() -> dict[str, dict]:
    """Get a dict of the indices of all specified template libraries.

    Paths to template libraries are obtained from `DSO_TEMPLATE_LIBRARIES` env variable.
    The paths can either be a python module, or a path to directory in the file system.
    """
    # as opposed to set(), this keeps the order of libraries as specified in DSO_TEMPLATE_LIBRARIES
    raw = os.environ.get("DSO_TEMPLATE_LIBRARIES", "dso.templates")
    lib_paths = list(dict.fromkeys(_split_template_libraries_env(raw)))

    libraries: dict[str, dict] = {}
    for lib_path in lib_paths:
        try:
            template_module = importlib.import_module(lib_path)
            tmp_dir = resources.files(template_module)
        except ImportError:
            tmp_dir = Path(lib_path).absolute()

        with (tmp_dir / "index.json").open("r", encoding="utf-8") as f:
            index = json.load(f)
            id_ = index["id"]
            if id_ in libraries:
                raise ValueError(f"ID {id_} is not unique for {lib_path}.")
            libraries[id_] = index
            libraries[id_]["path"] = tmp_dir
    return libraries


def _get_templates(library: dict, type_: Literal["init", "folder", "stage"]) -> dict:
    """
    From a given template library index, get a specified template.

    The template library index is one element in the dict obtained through `get_template_libraries).
    """
    templates: dict[str, dict] = {}
    for t in library[type_]:
        if t["id"] in templates:
            raise ValueError(f"ID {t['id']} is not unique for library {library['id']} and type {type_}.")
        templates[t["id"]] = t
        templates[t["id"]]["path"] = library["path"] / type_ / t["id"]

    return templates


def _copy_binary(source: Traversable, destination: Path) -> None:
    """Copy a binary file byte-for-byte."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    with source.open("rb") as rf, destination.open("wb") as wf:
        wf.write(rf.read())


def _copy_with_render(source: Traversable, destination: Path, params: dict) -> None:
    """Render a text file with Jinja2 and write it with LF newlines (UTF-8)."""
    from jinja2 import StrictUndefined, Template

    # If this looks like a binary file, copy without rendering or newline normalization
    suffix = Path(source.name).suffix.lower()
    if suffix in _BINARY_EXTS:
        _copy_binary(source, destination)
        return

    destination.parent.mkdir(parents=True, exist_ok=True)

    # Read as UTF-8 text; allow universal newlines on read
    with source.open("r", encoding="utf-8", newline="") as f:
        template = Template(f.read(), undefined=StrictUndefined)

    rendered_content = template.render(params)

    # Normalize line endings to LF and ensure a single trailing newline for non-empty files
    if rendered_content:
        # First normalize any CRLF/CR to LF
        rendered_content = rendered_content.replace("\r\n", "\n").replace("\r", "\n")
        # Ensure exactly one final newline
        if not rendered_content.endswith("\n"):
            rendered_content += "\n"

    # Write as UTF-8 with LF endings regardless of platform
    with destination.open("w", encoding="utf-8", newline="\n") as file:
        file.write(rendered_content)


def get_instantiate_template_help_text(type_):
    return dedent(
        f"""\
        Template libraries can be configured via the `DSO_TEMPLATE_LIBRARIES` environment variable. Please refer to the
        documentation for more details. If the environment variable is not set, the default template library is used.
        If only one template library is configured, it is not necessary to specify `--library`.

        Templates are obtained from the specified template library and selected based on the template's unique
        identifier. If only a single {type_} template is available from the template library, it is not necessary
        to specify `--template`.

        Templates can define an arbitrary number of parameters. These parameters are prompted for interactively.
        If you prefer, you can specify them as additional command line parameters, e.g. `--description`.
        """
    )


def prompt_for_template_params(
    type_: Literal["stage", "folder", "init"], library_id: str | None, template_id: str | None, **kwargs
):
    """
    Ask for all information required to instantiate a template.

    Ask for template library and template id
    Based on the template's json schema, ask for all variables that are not specified in kwargs.
    """
    import questionary
    from questionary import Choice

    libraries = _get_template_libraries()

    if library_id is None:
        if len(libraries) == 1:
            library_id = next(iter(libraries))
        else:
            library_id = questionary.select("Choose a template library:", choices=list(libraries)).ask()
            if library_id is None:
                sys.exit(1)  # user aborted prompt

    library = libraries[library_id]
    templates = _get_templates(library, type_)

    if template_id is None:
        if len(templates) == 1:
            template_id = next(iter(templates))
        else:
            choices = [Choice(t["id"], value=t["id"], description=t["description"]) for t in templates.values()]
            template_id = questionary.select(
                "Choose a template:",
                choices=choices,
                use_jk_keys=False,
                use_search_filter=True,
                show_selected=True,
                show_description=True,
            ).ask()

            if template_id is None:
                sys.exit(1)  # user aborted prompt

    template = templates[template_id]

    for p in template["params"]:
        name = p["name"]
        if name not in kwargs:
            res = questionary.text(p["description"]).ask()
            if res is None:
                sys.exit(1)  # user aborted prompt
            kwargs[name] = res

    return template, kwargs


def instantiate_template(template_path: Traversable, target_dir: Path | str, **params) -> None:
    """Copy a template folder to a target directory, filling all placeholder values.

    Text files are rendered (Jinja2) and written with LF newlines; binary files are copied byte-for-byte.
    """
    from jinja2 import Template

    target_dir = Path(target_dir)

    def _traverse_template(curr_path: Traversable, subdir: Path) -> None:
        for p in curr_path.iterdir():
            if p.is_file():
                # Render filename via Jinja
                name_rendered = Template(p.name).render(params)
                # this file is used for checking in empty folders in git.
                if name_rendered != ".gitkeeptemplate":
                    target_file = target_dir / subdir / name_rendered
                    if not target_file.exists():
                        _copy_with_render(p, target_file, params)
            else:
                (target_dir / subdir / p.name).mkdir(parents=True, exist_ok=True)
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
