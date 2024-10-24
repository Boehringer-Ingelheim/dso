"""Renames an existing stage or folder and update files accordingly"""

import sys
from os import getcwd
from pathlib import Path
import rich_click as click
from rich.prompt import Prompt
from dso._logging import log
from dso._util import get_project_root

check_files = [
    'params.in.yaml',
    'dvc.yaml'
]
check_directories = [
    'src',
]

def update_references(project_root: Path, old_name: str, new_name: str):
    """Update all references to the old name in the specified project files."""
    for file_path in project_root.rglob('*'):
        if file_path.is_file() and (
            any(part in file_path.parts for part in check_directories) or file_path.name in check_files
        ):
            try:
                content = file_path.read_text()
                updated_content = content.replace(old_name, new_name)
                file_path.write_text(updated_content)
            except Exception as e:
                log.error(f"[red]Failed to update {file_path}: {e}")

@click.argument("old_name", required=False)
@click.argument("new_name", required=False)
@click.command(
    "rename",
)
def cli(old_name: str | None = None, new_name: str | None = None):
    """Rename an existing stage or folder and update files accordingly."""

    if old_name is None:
        old_name = Prompt.ask(('[bold]Please enter the directory name of the stage or folder that shall be renamed'))
    if new_name is None:
        new_name = Prompt.ask(('[bold]Please enter the new stage or folder name'))
    project_root = get_project_root(Path(getcwd()))
    old_path = project_root / old_name
    new_path = project_root / new_name

    if not old_path.exists():
        log.error(f"[red]{old_name} does not exist!")
        sys.exit(1)

    if new_path.exists():
        log.error(f"[red]{new_name} already exists!")
        sys.exit(1)

    old_path.rename(new_path)
    update_references(project_root, old_name, new_name)
    log.info(f"[green]Renamed from {old_name} to {new_name} successfully.")

