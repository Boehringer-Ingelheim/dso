"""Python API, e.g. to be called from jupyter notebooks.

The functionality is the same as provided by the dso-r package.
"""

import os
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from tempfile import NamedTemporaryFile
from textwrap import dedent

from dso._get_config import get_config
from dso._logging import log
from dso._watermark import Watermarker

from ._util import get_project_root


@dataclass
class Config:
    """DSO config class"""

    stage_here: Path | None = None
    """Absolute path to the current stage"""

    dso_config: dict | None = None
    """DSO configuration read from stage params"""


CONFIG = Config()
"""Global configuration storage of the DSO API"""


def here(rel_path: str | Path | None = None) -> Path:
    """Get project root as a Path object

    Parameters
    ----------
    rel_path
        Relative path to be appended to the project root
    """
    proj_root = get_project_root(Path.cwd())
    if rel_path is None:
        return proj_root
    else:
        return proj_root / rel_path


def stage_here(rel_path: str | Path | None = None) -> Path:
    """
    Get the absolute path to the current stage

    The current stage is stored in `dso.CONFIG` and can be set using :func:`dso.set_stage` or
    :func:`dso.read_params`.

    Parameters
    ----------
    rel_path
        Relative path to be appended to the stage root
    """
    if CONFIG.stage_here is None:
        raise RuntimeError("No stage has been set. Run `read_params` or `set_stage` first!")
    if rel_path is None:
        return CONFIG.stage_here
    else:
        return CONFIG.stage_here / rel_path


def set_stage(stage: str | Path) -> None:
    """
    Set the active stage for `stage_here()`

    This sets the stage dir in `dso.CONFIG`.

    Parameters
    ----------
    stage
        Path to stage, relative to the project root
    """
    proj_root = get_project_root(Path.cwd())
    if not (proj_root / stage).exists():
        raise ValueError(
            dedent(
                f"""\
                The stage `{stage}` could not be found.

                Current working directory: `{Path.cwd()}`
                Inferred project root: `{proj_root}`
                """
            )
        )
    CONFIG.stage_here = proj_root / stage
    log.info(f"stage_here() starts at {CONFIG.stage_here}")


def read_params(stage: str | Path) -> dict:
    """
    Set stage dir and load parameters from the stage's params.yaml

    It is required to provide the path of the current stage relative to the project root to ensure that
    the correct config is loaded, no matter of the current working directory (as long as the working directory
    is any subdirectory of the project root). The function recompiles params.in.yaml to params.yaml on-the-fly
    to ensure that up-to-date params are always loaded.

    Only parameters that are declared as `params`, `dep`, or `output` in dvc.yaml are loaded to
    ensure that one does not forget to keep the `dvc.yaml` updated.

    Calls :func:`~dso.set_stage` internally.

    Parameters
    ----------
    stage
        Path to stage, relative to the project root
    """
    set_stage(stage)
    params = get_config(str(stage), skip_compile=bool(int(os.environ.get("DSO_SKIP_COMPILE", 0))))
    CONFIG.dso_config = params.get("dso", {})
    return params


@contextmanager
def WatermarkedFile(output_file: Path | str, **kwargs):
    """
    Contextmanager that handles adding watermarks to files.

    Currently supports SVG, PDF and all pixel graphics supported by pillow.

    Parameters
    ----------
    output_file
        Path to final (watermarked) image.
    kwargs
        Use this to customize watermarks. Takes precedence over the configuration in params.

    Yields
    ------
    Temporary filename to which the non-watermarked file needs to be written.
    If no watermark configuration is present (neither in params nor in kwargs),
    yields the output file path directly without applying any watermark.

    Example
    -------
    >>> fig, ax = plt.subplots()
    >>> ax.plot(range(10), range(10))
    >>> with dso.WatermarkedFile(stage_here("output/plot.pdf")) as f:
            fig.savefig(f, bbox_inches="tight")
    """
    output_file = Path(output_file)
    watermark_config = {}
    if CONFIG.dso_config is not None:
        watermark_config.update(CONFIG.dso_config.get("quarto", {}).get("watermark", {}))

    watermark_config.update(kwargs)

    if not watermark_config:
        yield output_file
    else:
        with NamedTemporaryFile(suffix=output_file.suffix) as f:
            try:
                yield f.name
            finally:
                Watermarker.add_watermark(f.name, output_file, **watermark_config)
