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


def _get_template_libraries() -> dict[str, dict]:
    """Get a dict of the indices of all specified template libraries.

    Paths to template libraries are obtained from `DSO_TEMPLATE_LIBRARIES` env variable.
    The paths can either be a python module, or a path to directory in the file system.
    """
    # as opposed to set(), this keep the order of libraries as specified in DSO_TEMPLATE_LIBRARIES
    lib_paths = list(dict.fromkeys(os.environ.get("DSO_TEMPLATE_LIBRARIES", "dso.templates").split(":")))

    libraries = {}
    for lib_path in lib_paths:
        try:
            template_module = importlib.import_module(lib_path)
            tmp_dir = resources.files(template_module)
        except ImportError:
            tmp_dir = Path(lib_path).absolute()

        with (tmp_dir / "index.json").open("rb") as f:
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
    templates = {}
    for t in library[type_]:
        if t["id"] in templates:
            raise ValueError(f"ID {t['id']} is not unique for library {library['id']} and type {type_}.")
        templates[t["id"]] = t
        templates[t["id"]]["path"] = library["path"] / type_ / t["id"]

    return templates


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
