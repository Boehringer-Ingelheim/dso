"""Creates a project folder structure"""

import sys
from os import getcwd
from pathlib import Path
from textwrap import dedent, indent

import rich_click as click
from rich.prompt import Confirm

from dso._logging import log
from dso._templates import (
    get_instantiate_template_help_text,
    instantiate_template,
    prompt_for_template_params,
)
from dso._util import get_project_root

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


@click.argument("name", required=False)
@click.option("--library", "-l", "library_id", help="Specify the id of a template library")
@click.option(
    "--template", "-t", "template_id", help="Specify the id of a template to use from the specified template library"
)
@click.command(
    "stage",
    help="Create a new stage.\n\nA stage can be in any subfolder of the projects. Stages shall not be nested.\n\n"
    + get_instantiate_template_help_text("stage"),
    context_settings={
        "ignore_unknown_options": True,
        "allow_extra_args": True,
    },
)
@click.pass_context
def dso_create_stage(ctx, name: str | None, *, template_id: str | None = None, library_id: str | None = None):
    """Create a new stage."""
    from dso._compile_config import compile_all_configs

    # get extra arguments, see https://stackoverflow.com/questions/32944131/add-unspecified-options-to-cli-command-using-python-click
    params = {ctx.args[i][2:]: ctx.args[i + 1] for i in range(0, len(ctx.args), 2)}
    if name is not None:
        params["name"] = name

    template, params = prompt_for_template_params("stage", library_id, template_id, **params)

    target_dir = Path(getcwd()) / params["name"]

    if target_dir.exists():
        log.error(f"[red]Couldn't create stage: Folder with name {target_dir} already exists!")
        sys.exit(1)

    target_dir.mkdir()

    # stage dir, relative to project root
    project_root = get_project_root(target_dir)
    stage_path = target_dir.relative_to(project_root)

    instantiate_template(template["path"], target_dir, rel_path_from_project_root=stage_path, **params)
    log.info("[green]Stage created successfully.")
    compile_all_configs([target_dir])


@click.argument("name", required=False)
@click.option("--library", "-l", "library_id", help="Specify the id of a template library")
@click.option(
    "--template", "-t", "template_id", help="Specify the id of a template to use from the specified template library"
)
@click.command(
    "folder",
    help=dedent("""\
    Create a new folder. A folder can contain subfolders or stages.

    Technically, nothing prevents you from just using `mkdir`. This command additionally adds some default
    files that might be useful, e.g. an empty `dvc.yaml`.

    You can specify a path to an existing folder. In that case all template files that do not exist will
    be copied to the folder. Existing files will never be overwritten.\n
    """)
    + get_instantiate_template_help_text("folder"),
    context_settings={
        "ignore_unknown_options": True,
        "allow_extra_args": True,
    },
)
@click.pass_context
def dso_create_folder(ctx, name: str | None, *, template_id: str | None = None, library_id: str | None = None):
    """Create a new folder. A folder can contain subfolders or stages."""
    # currently there's only one template for folders
    from dso._compile_config import compile_all_configs

    # get extra arguments, see https://stackoverflow.com/questions/32944131/add-unspecified-options-to-cli-command-using-python-click
    params = {ctx.args[i][2:]: ctx.args[i + 1] for i in range(0, len(ctx.args), 2)}
    if name is not None:
        params["name"] = name

    template, params = prompt_for_template_params("folder", library_id, template_id, **params)

    target_dir = Path(getcwd()) / params["name"]

    if target_dir.exists():
        if not Confirm.ask("[bold]Directory already exists. Do you want to copy template files to existing folder?"):
            sys.exit(1)

    target_dir.mkdir(exist_ok=True)

    # stage dir, relative to project root
    project_root = get_project_root(target_dir)
    folder_path = target_dir.relative_to(project_root)

    instantiate_template(template["path"], target_dir, rel_path_from_project_root=folder_path, **params)
    log.info("[green]Folder created successfully.")
    compile_all_configs([target_dir])


@click.group(name="create")
def dso_create():
    """Create stage folder structure subcommand."""
    pass


dso_create.add_command(dso_create_stage)
dso_create.add_command(dso_create_folder)
