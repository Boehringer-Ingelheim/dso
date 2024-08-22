"""Creates a project folder structure"""

import sys
from os import getcwd
from pathlib import Path
from textwrap import dedent, indent

import questionary
import rich_click as click
from rich.prompt import Confirm, Prompt

from dso._logging import log
from dso._util import _get_template_path, _instantiate_template, get_project_root
from dso.compile_config import compile_all_configs

DEFAULT_BRANCH = "master"
# list of stage template with description - can be later populated also from external directories
STAGE_TEMPLATES = {
    "bash": "Execute a simple bash snippet or call an external script (e.g. nextflow)",
    "quarto": "Generate a report using quarto",
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


@click.option("--description")
@click.option("--template", type=click.Choice(list(STAGE_TEMPLATES)))
@click.argument("name", required=False)
@click.command("stage", help=CREATE_STAGE_HELP_TEXT)
def create_stage(name: str | None = None, template: str | None = None, description: str | None = None):
    """Create a new stage."""
    if template is None:
        template = str(questionary.select("Choose a template:", choices=list(STAGE_TEMPLATES)).ask())

    if name is None:
        name = Prompt.ask('[bold]Please enter the name of the stage, e.g. "01_preprocessing"')

    if description is None:
        description = Prompt.ask("[bold]Please add a short description of the stage")

    target_dir = Path(getcwd()) / name
    if target_dir.exists():
        log.error(f"[red]Couldn't create stage: Folder with name {target_dir} already exists!")
        sys.exit(1)
    target_dir.mkdir()

    # stage dir, relative to project root
    project_root = get_project_root(target_dir)
    stage_path = target_dir.relative_to(project_root)

    _instantiate_template(
        _get_template_path("stage", template),
        target_dir,
        stage_name=name,
        stage_description=description,
        stage_path=stage_path,
    )
    log.info("[green]Stage created successfully.")
    compile_all_configs([target_dir])


@click.argument("name", required=False)
@click.command("folder")
def create_folder(name: str | None = None):
    """Create a new folder. A folder can contain subfolders or stages.

    Technically, nothing prevents you from just using `mkdir`. This command additionally adds some default
    files that might be useful, e.g. an empty `dvc.yaml`.

    You can specify a path to an existing folder. In that case all template files that do not exist will
    be copied to the folder. Existing files will never be overwritten.
    """
    # currently there's only one template for folders
    template = "default"

    if name is None:
        name = Prompt.ask('[bold]Please enter the name of the folder, e.g. "RNAseq"')

    target_dir = Path(getcwd()) / name

    if target_dir.exists():
        if not Confirm.ask("[bold]Directory already exists. Do you want to copy template files to existing folder?"):
            sys.exit(1)

    target_dir.mkdir(exist_ok=True)

    _instantiate_template(_get_template_path("folder", template), target_dir, stage_name=name)
    log.info("[green]Folder created successfully.")
    compile_all_configs([target_dir])


@click.group(name="create")
def cli():
    """Create stage folder structure subcommand."""
    pass


cli.add_command(create_stage)
cli.add_command(create_folder)
