import os
import re
import sys
from collections.abc import Collection
from itertools import groupby
from pathlib import Path

import rich_click as click
from ruamel.yaml import YAML

from dso._logging import log
from dso._util import get_project_root
from dso.compile_config import compile_all_configs


def _filter_nested_dict(data: dict, keys: Collection[str]) -> dict:
    """Filter a nested dictionary based on a list of dot-separated keys, e.g. `xxx.yyy`, `xxx.yyy.zzz`"""
    result = {}
    keys = sorted((x.split(".", maxsplit=1) for x in keys), key=lambda x: x[0])  # type: ignore
    for k, g in groupby(keys, lambda x: x[0]):
        g = list(g)
        # if the key (without any sub-keys) is part of the group, we add the entire field
        if [k] in g:
            result[k] = data[k]
        # otherwise we call the function recursively on the sub-fields.
        else:
            g = [x[1] for x in g]
            result[k] = _filter_nested_dict(data[k], g)
    # sort result to be in original order
    return {k: result[k] for k in data if k in result}


def get_config(stage: str, *, all: bool = False, skip_compile: bool = False) -> dict:
    """
    Get the configuration for a given stage

    By default, the configuration is filtered to include only the keys that are mentioned in `dvc.yaml` to force
    declaring all dependencies.

    Parameters
    ----------
    stage
        path to the stage relative to the project root. If multiple stages are defined in the `dvc.yaml` file,
        this should include the stage separated by a colon, e.g. `path/to/stage:stage_name`.
    all
        If true, the config is not filtered based on the `dvc.yaml` file.
    skip_compile
        If true, do not compile the config before loading it
    """
    proj_root = get_project_root(Path.cwd())
    log.info(f"Retrieving config for stage ./{stage}")
    if ":" in stage:
        stage_path, stage_name = stage.split(":")
    else:
        stage_path, stage_name = stage, None

    stage_path = proj_root / stage_path
    if not stage_path.exists():
        log.error(f"Path to stage does not exist: {stage_path}")
        sys.exit(1)

    if not skip_compile:
        log.debug("Skipping compilation of configuration")
        compile_all_configs([stage_path])
    yaml = YAML(typ="safe")

    try:
        config = yaml.load(stage_path / "params.yaml")
    except OSError:
        log.error("No params.yaml (or compilable params.in.yaml) found in directory.")
        sys.exit(1)

    if all:
        return config
    else:
        try:
            dvc_config = yaml.load(stage_path / "dvc.yaml")
        except OSError:
            log.error("No dvc.yaml found in directory.")
            sys.exit(1)

        try:
            dvc_stages = dvc_config.get("stages", None)
        except AttributeError:
            dvc_stages = None

        if not dvc_stages:
            log.error("At least one stage must be defined in `dvc.yaml` (unless --all is specified)")
            sys.exit(1)
        elif len(dvc_stages) > 1 and stage_name is None:
            log.error(
                "If multiple stages are defined in `dvc.yaml`, the stage name must be given using `path/to/stage:stage_name`"
            )
            sys.exit(1)
        elif len(dvc_stages) == 1:
            dvc_stage_config = next(iter(dvc_stages.values()))
        else:
            dvc_stage_config = dvc_stages[stage_name]

        # We want to include parameters mentioned in either `params`, `deps`, `outs`.
        # The parameters in `deps`/`outs` are encapsulated in `${ <param> }`
        keep_params = set(dvc_stage_config.get("params", []))
        dvc_param_pat = re.compile(r"\$\{\s*(.*?)\s*\}")
        for dep in dvc_stage_config.get("deps", []):
            if match := dvc_param_pat.findall(dep):
                keep_params.update(match)
        for out in dvc_stage_config.get("outs", []):
            if match := dvc_param_pat.findall(out):
                keep_params.update(match)

        log.info(
            f"Only including the following parameters which are listed in `dvc.yaml`: [green]{', '.join(keep_params)}"
        )

        return _filter_nested_dict(config, keep_params)


@click.command(name="get-config")
@click.option(
    "--all",
    is_flag=True,
    type=bool,
    default=False,
    help="Include all parameters, not only those mentioned in `dvc.yaml`",
)
@click.option(
    "--skip-compile",
    is_flag=True,
    type=bool,
    default=bool(int(os.environ.get("DSO_SKIP_COMPILE", 0))),
    help="Do not compile configs before loading it. The same can be achieved by setting the `DSO_SKIP_COMPILE=1` env var.",
)
@click.argument(
    "stage",
)
def cli(stage, all, skip_compile):
    """Get the configuration for a given stage and print it to STDOUT in yaml format.

    The path to the stage must be relative to the root dir of the project.

    By default, the configuration is filtered to include only the keys that are mentioned in `dvc.yaml` to force
    declaring all dependencies.

    If multiple stages are defined in a single `dvc.yaml`, the stage name MUST be specified using
    `path/to/stage:stage_name` unless `--all` is given.
    """
    try:
        out_config = get_config(stage, all=all, skip_compile=skip_compile)
        yaml = YAML()
        yaml.dump(out_config, sys.stdout)
    except KeyError as e:
        log.error(f"dvc.yaml defines parameter {e} that is not in params.yaml")
        sys.exit(1)
