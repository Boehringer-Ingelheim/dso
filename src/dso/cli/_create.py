"""Creates a project folder structure"""

import importlib
import json
import os
import sys
from importlib import resources
from os import getcwd
from pathlib import Path
from textwrap import dedent, indent
from typing import Literal

import rich_click as click
from rich.prompt import Confirm, Prompt

from dso._logging import log
from dso._util import get_project_root, get_template_path, instantiate_template

# list of stage template with description - can be later populated also from external directories
STAGE_TEMPLATES = {
    "bash": "Execute a simple bash snippet or call an external script (e.g. nextflow)",
    "quarto_r": "Generate a quarto report using R (qmd file)",
    "quarto_py": "Generate a quarto report using Python (qmd file)",
    "quarto_ipynb": "Generate a quarto report using Python (ipynb file)",
}
# Create help text for CLI listing all templates
STAGE_TEMPLATE_TEXT = "\n".join(f" * __{name}__: {description}" for name, description in STAGE_TEMPLATES.items())
CREATE_STAGE_HELP_TEXT = dedent(
    f"""\
    Create a new stage.

    A stage can be in any subfolder of the projects. Stages shall not be nested.

    Available templates: \n{indent(STAGE_TEMPLATE_TEXT, " " * 6)}
    """
)


def _get_template_libraries() -> dict[str, dict]:
    """Get a list of stages from template library(s)

    Paths to template libraries are obtained from `DSO_TEMPLATE_LIBRARIES` env variable.
    The paths can either be a python module, or a path to directory in the file system.
    """
    lib_paths = set(os.environ.get("DSO_TEMPLATE_LIBRARIES", "dso.templates").split(":"))

    libraries = {}
    for lib_path in lib_paths:
        try:
            template_module = importlib.import_module(lib_path)
            tmp_dir = resources.files(template_module)
        except ImportError:
            raise NotImplementedError from None

        with (tmp_dir / "index.json").open("rb") as f:
            index = json.load(f)
            id_ = index["id"]
            if id_ in libraries:
                raise ValueError(f"ID {id_} is not unique for {lib_path}.")
            libraries[id_] = index
            libraries[id_]["path"] = lib_path
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

    return templates


@click.option("--template", "-t", "template_id", type=click.Choice(list(STAGE_TEMPLATES)))
@click.option("--library", "-l", "library_id", help="Choose the template library to use")
@click.command(
    "stage",
    help=CREATE_STAGE_HELP_TEXT,
    context_settings={
        "ignore_unknown_options": True,
        "allow_extra_args": True,
    },
)
@click.pass_context
def dso_create_stage(ctx, template_id: str | None = None, library_id: str | None = None):
    """Create a new stage."""
    import questionary
    from questionary import Choice

    from dso._compile_config import compile_all_configs

    # get extra arguments, see https://stackoverflow.com/questions/32944131/add-unspecified-options-to-cli-command-using-python-click
    kwargs = {ctx.args[i][2:]: ctx.args[i + 1] for i in range(0, len(ctx.args), 2)}

    libraries = _get_template_libraries()

    if len(libraries) == 1:
        library_id = next(iter(libraries))
    if library_id is None:
        library_id = str(questionary.select("Choose a template library:", choices=list(libraries)).ask())

    library = libraries[library_id]
    templates = _get_templates(library, "stage")

    if template_id is None:
        choices = [Choice(t["id"], value=t["id"], description=t["description"]) for t in templates.values()]
        template_id = str(
            questionary.select(
                "Choose a template:",
                choices=choices,
                use_jk_keys=False,
                use_search_filter=True,
                show_selected=True,
                show_description=True,
            ).ask()
        )
        template = templates[template_id]

    for p in template["params"]:
        name = p["name"]
        if name not in kwargs:
            kwargs[name] = questionary.text(p["description"]).ask()

    target_dir = Path(getcwd()) / name
    if target_dir.exists():
        log.error(f"[red]Couldn't create stage: Folder with name {target_dir} already exists!")
        sys.exit(1)
    target_dir.mkdir()

    # stage dir, relative to project root
    project_root = get_project_root(target_dir)
    stage_path = target_dir.relative_to(project_root)

    instantiate_template(libraries[library_id]["path"], target_dir, rel_path_from_project_root=stage_path, **kwargs)
    log.info("[green]Stage created successfully.")
    compile_all_configs([target_dir])


@click.argument("name", required=False)
@click.command("folder")
@click.option("--library", help="Choose the template library to use")
@click.option("--template", type=click.Choice(list(STAGE_TEMPLATES)))
def dso_create_folder(name: str | None = None, template: str | None = None, library: str | None = None):
    """Create a new folder. A folder can contain subfolders or stages.

    Technically, nothing prevents you from just using `mkdir`. This command additionally adds some default
    files that might be useful, e.g. an empty `dvc.yaml`.

    You can specify a path to an existing folder. In that case all template files that do not exist will
    be copied to the folder. Existing files will never be overwritten.
    """
    # currently there's only one template for folders
    from dso._compile_config import compile_all_configs

    template = "default"

    if name is None:
        name = Prompt.ask('[bold]Please enter the name of the folder, e.g. "RNAseq"')

    target_dir = Path(getcwd()) / name

    if target_dir.exists():
        if not Confirm.ask("[bold]Directory already exists. Do you want to copy template files to existing folder?"):
            sys.exit(1)

    target_dir.mkdir(exist_ok=True)

    instantiate_template(get_template_path("folder", template), target_dir, folder_name=name)
    log.info("[green]Folder created successfully.")
    compile_all_configs([target_dir])


@click.group(name="create")
def dso_create():
    """Create stage folder structure subcommand."""
    pass


dso_create.add_command(dso_create_stage)
dso_create.add_command(dso_create_folder)
