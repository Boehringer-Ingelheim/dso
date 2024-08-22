"""Initializes the project folder structure and git"""

import sys
from os import getcwd
from pathlib import Path

import rich_click as click
from rich.prompt import Confirm, Prompt

from dso._logging import log
from dso._util import _get_template_path, _instantiate_with_repo
from dso.compile_config import compile_all_configs

DEFAULT_BRANCH = "master"


@click.option("--description")
@click.argument("name", required=False)
@click.command(
    "init",
)
def cli(name: str | None = None, description: str | None = None):
    """
    Initialize a new project. A project can contain several stages organized in arbitrary subdirectories.

    If you wish to initialize DSO in an existing project, you can specify an existing directory. In
    this case, it will initialize files from the template that do not exist yet, but never overwrite existing files.
    """
    if name is None:
        name = Prompt.ask('[bold]Please enter the name of the project, e.g. "single_cell_lung_atlas"')

    target_dir = Path(getcwd()) / name

    if target_dir.exists():
        if not Confirm.ask("[bold]Directory already exists. Do you want to initialize DSO in an existing project?"):
            sys.exit(1)

    if description is None:
        description = Prompt.ask("[bold]Please add a short description of the project")

    _instantiate_with_repo(
        _get_template_path("init", "default"), target_dir, project_name=name, project_description=description
    )
    log.info("[green]Project initalized successfully.")
    compile_all_configs([target_dir])
