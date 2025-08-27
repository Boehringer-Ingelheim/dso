"""Get configuration for a stage based on params.in.yaml and dvc.yaml"""

from __future__ import annotations

import re
import sys
from collections.abc import Collection
from itertools import groupby
from pathlib import Path

from ruamel.yaml import YAML

from dso._logging import log
from dso._util import get_project_root


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
    r"""
    Get the configuration for a given stage.

    Resolution rules for the `stage` argument:
      - If it contains a stage name (e.g. `path/to/dir:stage_name`), split on the
        *stage* separator colon **without** confusing Windows drive letters like `C:\`.
      - If the path part is ABSOLUTE, use it as-is.
      - If the path part is RELATIVE, resolve **first** against the current working
        directory, and if not found, resolve against the project root (where `.git` lives).

    By default, the configuration is filtered to include only keys mentioned in the
    corresponding stage in `dvc.yaml`. Use `all=True` to return the full config.

    Parameters
    ----------
    stage : str
        Path to the stage directory (absolute or relative), optionally followed by
        `:stage_name` if multiple stages exist in the directory's `dvc.yaml`.
    all : bool
        If true, the config is not filtered based on the `dvc.yaml` file.
    skip_compile : bool
        If `True`, do not compile the config before loading it. If `False`, always compile.
    """
    from dso._compile_config import compile_all_configs

    proj_root = get_project_root(Path.cwd())

    # --- robustly split "path[:stage_name]" without breaking on Windows drive letters ---
    def split_stage_arg(arg: str) -> tuple[str, str | None]:
        # If it starts with a Windows drive like 'C:\' or 'D:/', ignore that first colon
        if re.match(r"^[A-Za-z]:[\\/]", arg):
            idx = arg.find(":", 2)  # search ':' after 'C:' prefix
            if idx != -1:
                return arg[:idx], arg[idx + 1 :]
            return arg, None
        # Non-windows-absolute (or relative): split on the last ':' to be safe
        if ":" in arg:
            left, right = arg.rsplit(":", 1)
            return left, right
        return arg, None

    stage_part, stage_name = split_stage_arg(stage)

    # Build a concrete directory path for the stage with CWD-first resolution for relative paths
    stage_path_candidate = Path(stage_part)

    if stage_path_candidate.is_absolute():
        stage_path = stage_path_candidate
    else:
        # 1) Try relative to CWD
        cwd_candidate = (Path.cwd() / stage_path_candidate).resolve()
        if cwd_candidate.is_dir():
            stage_path = cwd_candidate
        else:
            # 2) Fall back to relative to project root
            stage_path = (proj_root / stage_path_candidate).resolve()

    # Friendly logging: show relative-to-project if possible
    try:
        disp = f"./{stage_path.relative_to(proj_root)}"
    except ValueError:
        disp = str(stage_path)
    log.info(f"Retrieving config for stage {disp}")

    if not stage_path.exists() or not stage_path.is_dir():
        log.error(f"Path to stage does not exist: {stage_path}")
        sys.exit(1)

    if not skip_compile:
        log.debug("Compiling configuration")
        compile_all_configs([stage_path])
    else:
        log.debug("Skipping compilation of configuration")

    yaml = YAML(typ="safe")

    try:
        config = yaml.load(stage_path / "params.yaml")
    except OSError:
        log.error("No params.yaml (or compilable params.in.yaml) found in directory.")
        sys.exit(1)

    if all:
        return config

    # Read dvc.yaml to determine which parameters to keep
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
        dvc_stage_config = dvc_stages.get(stage_name)
        if dvc_stage_config is None:
            log.error(f"Stage '{stage_name}' not found in dvc.yaml.")
            sys.exit(1)

    # We want to include parameters mentioned in either `params`, `deps`, `outs`.
    # The parameters in `deps`/`outs` are encapsulated in `${ <param> }`
    is_matrix_stage = "matrix" in dvc_stage_config
    if (params := dvc_stage_config.get("params", [])) is None:
        keep_params = set()
    else:
        keep_params = set(params)

    dvc_param_pat = re.compile(r"\$\{\s*(.*?)\s*\}")
    for dep in dvc_stage_config.get("deps", []) or []:
        if match := dvc_param_pat.findall(dep):
            keep_params.update(match)
    for out in dvc_stage_config.get("outs", []) or []:
        if match := dvc_param_pat.findall(out):
            keep_params.update(match)

    log.info(
        f"Only including the following parameters which are listed in `dvc.yaml`: [green]{', '.join(sorted(keep_params))}"
    )

    if is_matrix_stage:
        keep_params = {p for p in keep_params if not (p.startswith("item.") or p == "item")}

    return _filter_nested_dict(config, keep_params)
