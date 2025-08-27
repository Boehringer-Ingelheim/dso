import contextlib
import filecmp
import os
import tempfile
from collections.abc import Collection, Sequence
from functools import partial
from io import TextIOWrapper
from pathlib import Path
from textwrap import dedent

import hiyapyco
from ruamel.yaml import YAML, yaml_object

from ._logging import log
from ._util import (
    check_project_roots,
    find_in_parent,
    get_dso_config_from_pyproject_toml,
    get_project_root,
)

PARAMS_YAML_DISCLAIMER = dedent(
    """\
    ################################# !!! WARNING !!! #############################################
    #                                                                                             #
    # params.yaml is AUTOMATICALLY GENERATED. DO NOT EDIT BY HAND or your changes might be lost.  #
    #                                                                                             #
    # Instead, edit `params.in.yaml` and compile the changes using `dso compile-config`.          #
    # If you do not wish to use this feature, simply delete `params.in.yaml`                      #
    # and remove this notice                                                                      #
    ###############################################################################################
    """
)


def _normalize_windows_separators(obj):
    r"""
    Recursively replace forward slashes with backslashes in strings on Windows.

    Heuristics:
    - Skip URLs ('://')
    - Skip UNC/pseudo-URL prefixes ('//') and existing UNC ('\\\\')
    """
    if isinstance(obj, dict):
        return {k: _normalize_windows_separators(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_normalize_windows_separators(v) for v in obj]
    if isinstance(obj, str):
        if "://" in obj or obj.startswith(("//", "\\\\")):
            return obj
        return obj.replace("/", "\\")
    return obj


def _format_path_for_yaml(path: Path, *, base: Path, relative: bool) -> str:
    r"""
    Return a string to be written into YAML using OS-native separators:

    - relative=True  -> relative path with OS-native separators
    - relative=False -> absolute native path (Windows => '\\', POSIX => '/')
    """
    path = Path(path).resolve()
    base = Path(base).resolve()

    if relative:
        # On Windows, relpath raises ValueError if paths are on different drives.
        try:
            rel = os.path.relpath(path, start=base)
        except ValueError:
            # Fall back to absolute if no sensible relpath can be formed.
            return str(path)
        return rel  # already OS-native
    else:
        return str(path)  # absolute, OS-native


def _load_yaml_with_auto_adjusting_paths(
    yaml_stream: TextIOWrapper,
    destination: Path,
    missing_path_warnings: set[tuple[Path, Path]],
    relative: bool = True,
):
    """
    Load a yaml file and adjust paths for all !path objects based on a destination file

    Parameters
    ----------
    yaml_stream
        Opened stream of the yaml file to load (ruamel provides .name)
    destination
        Path to which the file shall be adjusted
    missing_path_warnings
        set in which we keep track of warnings for missing paths to ensure we are
        not emitting the same warning twice.
    relative
        If True, compile to relative paths. Otherwise compile to absolute paths.

    Returns
    -------
    The output of ruamel.yaml.YAML.load_all after registering a class for !path
    """
    ruamel = YAML()

    # The folder of the source config file
    source = Path(yaml_stream.name).parent
    # stage name for logging purposes only
    stage = source.relative_to(get_project_root(source))

    if not destination.is_relative_to(source):
        raise ValueError("Destination path can be the same as source, or a child thereof.")

    @yaml_object(ruamel)
    class AutoAdjustingPathWithLocation(str):
        """
        Represents a YAML node that adjusts a relative path relative to a specified destination directory.

        Works with hiyapyco interpolation because we inherit from str.
        """

        yaml_tag = "!path"

        def __init__(self, path: str):
            self.path = Path(path)
            if not (source / self.path).exists():
                # check if warning for the same path was already emitted
                if (self.path, source) not in missing_path_warnings:
                    # Warn, but do not fail (it could also be an output path to be populated by a dvc stage)
                    log.warning(f"Path {self.path} in stage {stage} does not exist!")
                    missing_path_warnings.add((self.path, source))

        def _adjusted_str(self) -> str:
            target = source / self.path
            return _format_path_for_yaml(target, base=destination, relative=relative)

        def get_adjusted(self) -> str:
            """Return the adjusted path as a string with OS-native separators."""
            adj = (source / self.path).resolve()
            return str(adj) if not relative else os.path.relpath(adj, start=destination.resolve())

        @classmethod
        def to_yaml(cls, representer, node):
            # Serialize as normalized string (OS-native separators)
            return representer.represent_str(node._adjusted_str())

        def __repr__(self):
            return self._adjusted_str()

        def __str__(self):
            return self._adjusted_str()

        @classmethod
        def from_yaml(cls, constructor, node):
            return cls(node.value)

    return ruamel.load_all(yaml_stream)


def _get_list_of_configs_to_compile(paths: Sequence[Path], project_root: Path):
    """Find all files named params.in.yaml in `dir` and all subdirectories"""
    # Get all configs that are children of the provided paths
    all_configs = {x for dir in paths for x in dir.glob("**/params.in.yaml")}
    for c in all_configs:
        assert c.is_relative_to(project_root), "Config file not relative to project root"

    # Also include any parent configs for hierarchical compilation.
    for tmp_path in paths:
        while (tmp_path := find_in_parent(tmp_path.parent, "params.in.yaml", project_root)) is not None:
            all_configs.add(tmp_path)
            tmp_path = tmp_path.parent

    return all_configs


def _get_parent_configs(current_config: Path, all_configs: Collection[Path]) -> list[Path]:
    """For a particular config file, find all config files that are parent to it in a list of config files.

    The files are sorted from parent to child. The current_config is always the last item in the list.
    """
    parent_configs = []
    for tmp_cfg in all_configs:
        if current_config.is_relative_to(tmp_cfg.parent):
            parent_configs.append(tmp_cfg)

    # sort from parent to child (based on the number of path parts)
    return sorted(parent_configs, key=lambda x: len(x.parts))


def compile_all_configs(paths: Sequence[Path]):
    """Compile params.in.yaml into params.yaml using Jinja2 templating and resolving recursive templates.

    paths:
        One or multiple locations within the project. Can be files or directories -- instead of files, their
        parent directory will be used. Will compile all params.in.yaml files in child directories
        and the respective parent config files.
    """
    # If files are specified, use the respective parent dir
    paths = [p.parent.resolve() if p.is_file() else p.resolve() for p in paths]

    project_root = check_project_roots(paths)
    log.info(f"Detected {project_root} as project root.")

    all_configs = _get_list_of_configs_to_compile(paths, project_root)
    log.info(f"Compiling a total of {len(all_configs)} config files.")

    dso_config = get_dso_config_from_pyproject_toml(project_root)
    use_relative_paths = dso_config.get("use_relative_paths", True)

    missing_path_warnings: set[tuple[Path, Path]] = set()

    for config in all_configs:
        # Parent to child order; hiyapyco gives precedence to later items.
        configs_to_merge = _get_parent_configs(config, all_configs)

        conf = hiyapyco.load(
            *[str(x) for x in configs_to_merge],
            method=hiyapyco.METHOD_MERGE,
            none_behavior=hiyapyco.NONE_BEHAVIOR_OVERRIDE,
            interpolate=True,
            loader_callback=partial(
                _load_yaml_with_auto_adjusting_paths,
                destination=config.parent,
                missing_path_warnings=missing_path_warnings,
                relative=use_relative_paths,
            ),
        )

        if conf is None:
            conf = {}

        # Make all path-like strings use backslashes on Windows
        if os.name == "nt":
            conf = _normalize_windows_separators(conf)

        out_file = config.parent / "params.yaml"
        out_dir = out_file.parent
        out_dir.mkdir(parents=True, exist_ok=True)

        # --- Write to a temp file in the SAME DIRECTORY as out_file (portable & atomic) ---
        fd, tmp_name = tempfile.mkstemp(dir=out_dir, prefix=".params-", suffix=".yaml")
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
                f.write(PARAMS_YAML_DISCLAIMER)
                f.write("\n")
                YAML().dump(conf, f)
                f.flush()
                os.fsync(f.fileno())

            needs_update = not out_file.exists() or not filecmp.cmp(tmp_name, out_file, shallow=False)

            if needs_update:
                os.replace(tmp_name, out_file)
                log.debug(f"Compiled ./{config.relative_to(project_root)} to {out_file.name}")
            else:
                log.debug(f"./{config.relative_to(project_root)} [green]is already up-to-date!")
                with contextlib.suppress(OSError):
                    os.remove(tmp_name)  # cleanup temp

        finally:
            # If replace/move already consumed tmp_name, this is a no-op
            with contextlib.suppress(OSError):
                if os.path.exists(tmp_name):
                    os.remove(tmp_name)

    log.info("[green]Configuration compiled successfully.")
