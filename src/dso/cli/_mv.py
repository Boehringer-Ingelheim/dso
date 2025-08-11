"""Rename stage or folder"""

import os
import sys
from os import getcwd
from pathlib import Path

import rich_click as click

from dso._logging import log
from dso._util import get_project_root


def update_all_references_to_source(project_root: Path, source_absolute_path: Path, target_absolute_path: Path):
    """In the whole project, search for relative references to the old location and update to relative reference to the new location."""
    log.debug("[yellow]Updating all references to source")
    log.debug(f"{project_root} - {source_absolute_path} - {target_absolute_path}")
    for dvc_dir in project_root.rglob("*"):
        if dvc_dir.is_dir() and (dvc_dir / "dvc.yaml").exists() and dvc_dir != target_absolute_path:
            source_direct_path = os.path.relpath(source_absolute_path, start=dvc_dir)
            target_direct_path = os.path.relpath(target_absolute_path, start=dvc_dir)

            log.info(f"Relatives path from {dvc_dir}: {source_direct_path} to {target_direct_path}")

            update_references_in_file(dvc_dir / "dvc.yaml", source_direct_path, target_direct_path)
            update_references_in_file(dvc_dir / "params.in.yaml", source_direct_path, target_direct_path)

            # Iterate over all non-hidden files in the src subdirectory of dvc_dir
            src_subdir = dvc_dir / "src"
            if src_subdir.exists() and src_subdir.is_dir():
                for file_path in src_subdir.rglob("*"):
                    if file_path.is_file() and not file_path.name.startswith("."):
                        update_references_in_file(file_path, source_direct_path, target_direct_path)


def update_references_in_file(file: Path, pattern: str, replacement: str):
    """Update all pattern in file"""
    if os.path.exists(file):
        log.debug(f"Updating {file}: replacing '{pattern}' with '{replacement}'")
        try:
            content = Path(file).read_text()
            updated_content = content.replace(pattern, replacement)
            Path(file).write_text(updated_content)
        except (OSError, UnicodeDecodeError) as e:
            log.error(f"[red]Failed to update {file}: {e}")
    else:
        log.error(f"[red]Trying to replace references in '{file}', but files does not exist. Exiting.")
        sys.exit(1)


def update_files_in_src_folder(path: Path, source_base: str, target_base: str, source_relative: Path, target_relative: Path):
    """Rename all files which contain stage name, for all update the stage"""
    if path.exists():
        for file_path in path.rglob("*"):
            if file_path.is_file() and not file_path.name.startswith("."):
                new_file_name = file_path.name.replace(str(source_base), str(target_base))
                new_file_path = file_path.parent / new_file_name
                log.debug(f"Renaming file {file_path} to {new_file_path}")
                try:
                    file_path.rename(new_file_path)
                except OSError as e:
                    log.error(f"[red]Failed to rename {file_path}: {e}")

                update_references_in_file(new_file_path, str(source_relative), str(target_relative))
    else:
        log.error(f"[red]Src directory {path} does not exist.")
        sys.exit(1)


def update_source(
    source_base: str,
    target_base: str,
    source_relative_path: Path,
    target_relative_path: Path,
    source_absolute_path: Path,
    target_absolute_path: Path,
):
    log.debug("[yellow]Updating source")

    log.debug(f"Renaming {source_absolute_path} to {target_absolute_path}")
    source_absolute_path.rename(target_absolute_path)

    dvc_file_path = target_absolute_path / "dvc.yaml"
    log.debug(f"Renaming possible stage in {dvc_file_path}")
    update_references_in_file(dvc_file_path, str(source_base), str(target_base))

    src_path = target_absolute_path / "src"

    if src_path.exists():
        update_files_in_src_folder(src_path, source_base, target_base, source_relative_path, target_relative_path)

    if source_relative_path.parent != target_relative_path.parent:
        log.warning(
            "[red] ATTENTION: target directory is changing. References of renamed item to other stages must be updated manually."
        )

    readme_path = target_absolute_path / "README.md"

    update_references_in_file(readme_path, str(source_base), str(target_base))


@click.command(name="mv")
@click.argument("source", type=click.Path(exists=True, file_okay=True, dir_okay=True, path_type=Path))
@click.argument("target", type=click.Path(file_okay=True, dir_okay=True, path_type=Path))
def dso_mv(source: Path, target: Path):
    """Move and rename a stage or a folder and update references to it

    A stage or folder is renamed with references to it. In a stage, the dvc.yaml, params.in.yaml
    and src files. In other folder or stages, dvc.yaml, params.in.yaml and src files are updated.
    """
    log.info(f"[yellow]Renaming from '{source}' to '{target}'.")
    log.info(
        "[red]Warning: This renaming feature is experimental. If a stage is moved to a different folder, you may need to manually update references to other files."
    )

    # Make path absolute, resolving all symlinks
    source = Path(source).resolve()
    target = Path(target).resolve()

    project_root = get_project_root(Path(getcwd()))

    # assert that source and target are in project_root
    if project_root not in source.parents:
        log.error(f"[red]{source} is not within the project root {project_root}!")
        sys.exit(1)

    if project_root not in target.parents:
        log.error(f"[red]{target} is not within the project root {project_root}!")
        sys.exit(1)

    source_relative_path = source.relative_to(project_root)
    target_relative_path = target.relative_to(project_root)

    target_relative_dir = target_relative_path.parent

    log.debug(f"Relative source path: {source_relative_path}")
    log.debug(f"Relative target path: {target_relative_path}")

    source_absolute_path = project_root / source_relative_path
    target_absolute_path = project_root / target_relative_path
    target_absolute_dir = project_root / target_relative_dir

    source_base = source_absolute_path.name
    target_base = target_absolute_path.name

    log.debug(f"Base source: {source_base}")
    log.debug(f"Base target: {target_base}")
    log.debug(f"Absolute source path: {source_absolute_path}")
    log.debug(f"Absolute target path: {target_absolute_path}")
    log.debug(f"Absolute target base directory: {target_absolute_dir}")

    if not source_absolute_path.exists():
        log.error(f"[red]{source} does not exist!")
        sys.exit(1)

    # Currently is not allowed to move the folder or stage to a directory
    # which does not exist.
    if not target_absolute_dir.exists():
        log.error(f"[red]{target_relative_dir} does not exist. Target base directory must already exist.")
        sys.exit(1)

    if target_absolute_path.exists():
        log.error(f"[red]{target} already exists!")
        sys.exit(1)

    update_source(
        source_base, target_base, source_relative_path, target_relative_path, source_absolute_path, target_absolute_path
    )

    update_all_references_to_source(project_root, source_absolute_path, target_absolute_path)

    log.debug(f"[green]Moved from {source} to {target} successfully.")
