import filecmp
import os.path
import shutil
import tempfile
from collections.abc import Collection, Sequence
from functools import partial
from io import TextIOWrapper
from pathlib import Path
from textwrap import dedent

import hiyapyco
from ruamel.yaml import YAML, yaml_object

from ._logging import log
from ._util import check_project_roots, find_in_parent, get_dso_config_from_pyproject_toml, get_project_root

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
    yaml_path
        Path of the yaml file to load
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

    # inherit from `str` to make this compatible with hiyapyco interpolation
    @yaml_object(ruamel)
    class AutoAdjustingPathWithLocation(str):
        """
        Represents a YAML node that adjusts a relative path relative to a specified destination directory.

        Can be evaulated either using Ruamel during dumping YAML to file, or whenever it is cast
        to a string (e.g. by hiyapyco). To this end, __repr__ and __str__ are overridden.
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

        def get_adjusted(self):
            if relative:
                # not possible with pathlib, because pathlib requires the paths to be subpaths of each other
                return Path(os.path.relpath(source / self.path, destination))
            else:
                return (source / self.path).absolute()

        @classmethod
        def to_yaml(cls, representer, node):
            return representer.represent_str(str(node.get_adjusted()))

        def __repr__(self):
            return str(self.get_adjusted())

        def __str__(self):
            return str(self.get_adjusted())

        @classmethod
        def from_yaml(cls, constructor, node):
            return cls(node.value)

    return ruamel.load_all(yaml_stream)


def _get_list_of_configs_to_compile(paths: Sequence[Path], project_root: Path):
    """Find all files named params.in.yaml in `dir` and all subdirectories"""
    # Get all configs that are children of the current working directory
    all_configs = {x for dir in paths for x in dir.glob("**/params.in.yaml")}
    for c in all_configs:
        assert c.is_relative_to(project_root), "Config file not relative to project root"

    # Now we still need to find all config.in.yaml files in any parent directory (to enable the hierarchical compilation).
    # We can start with the input paths, as they are per definition a parent of all config files found.
    for tmp_path in paths:
        # Check each parent directory if it contains a "params.in.yaml" - If yes, add it to the list of all configs.
        # We don't need to re-check the parents of added items, because their parent is per definition also a parent
        # of a config that was already part of the list.
        while (tmp_path := find_in_parent(tmp_path.parent, "params.in.yaml", project_root)) is not None:
            all_configs.add(tmp_path)
            # we don't want to find the current config again, therefore .parent
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
    # by default, use relative paths
    use_relative_paths = dso_config.get("use_relative_paths", True)

    # keep track of paths for which we emitted a warning that the path doesn't exist to ensure
    # we are only emitting one warning for each (file path, source yaml file path)
    missing_path_warnings: set[tuple[Path, Path]] = set()

    for config in all_configs:
        # sorted sorts path from parent to child. This is what we want as hyapyco gives precedence to configs
        # later in the list.
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
        # an empty configuration should actually be an empty dictionary.
        if conf is None:
            conf = {}
        # write config to "params.yaml" in same directory
        out_file = config.parent / "params.yaml"

        # Write to temporary file first and compare to previous params.yaml
        # Only ask for confirmation, overwrite, and show log if they are different
        with tempfile.NamedTemporaryFile() as tmpfile:
            # dump to tempfile
            with open(tmpfile.name, "w") as f:
                f.write(PARAMS_YAML_DISCLAIMER)
                f.write("\n")
                ruamel = YAML()
                ruamel.dump(conf, f)
            # check for equivalience
            if not out_file.exists() or not filecmp.cmp(f.name, out_file, shallow=False):
                shutil.copy(tmpfile.name, out_file)
                log.debug(f"Compiled ./{config.relative_to(project_root)} to {out_file.name}")
            else:
                log.debug(f"./{config.relative_to(project_root)} [green]is already up-to-date!")

    log.info("[green]Configuration compiled successfully.")
