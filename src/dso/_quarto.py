"""Helper functions for rendering quarto documents"""

import os
import stat
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path
from textwrap import dedent, indent

from ruamel.yaml import YAML


def render_quarto(
    quarto_dir: Path,
    report_dir: Path,
    before_script: str,
    cwd: Path,
    with_pandocfilter: bool = False,
):
    """
    Render a quarto project

    Parameters
    ----------
    quarto_dir
        Path that contains the _quarto.yml document
    report_dir
        Output directory of the rendered document
    before_script
        Bash snippet to execute before running quarto (e.g. to setup the enviornment)
    """
    if not before_script:
        before_script = ""
    before_script = indent(before_script, " " * 8)
    report_dir = report_dir.absolute()
    report_dir.mkdir(exist_ok=True)

    # clean up existing `.rmarkdown` files that may interfere with rendering
    # these are leftovers from a previous, failed `quarto render` attempt. If they still exist, the next attempt
    # fails. We remove them *before* the run instead of cleaning them up *after* the run, because they
    # may be useful for debugging failures.
    # see https://github.com/Boehringer-Ingelheim/dso/issues/54
    for f in quarto_dir.glob("*.rmarkdown"):
        if f.is_file():
            f.unlink()

    # Enable pandocfilter if requested.
    # We create temporary scripts that then call the current python binary with the dso.pandocfilter module
    # This may seem cumbersome, but we do it this way because
    #  * pandoc only supports a single binary for a filter, referring to subcommands or `-m` is not possible here
    #  * we want to ensure that exactly the same python/dso version is used for the pandocfilter as for the
    #    parent command (important when running through dso-mgr)
    # The filter runs in two stages:
    #  * `disclaimer` is registered in `_quarto.yml` at the `pre-ast` entry point. Only then quarto processes
    #    the disclaimer callout, which is required for it to be rendered in all output formats (e.g. PDF).
    #    See https://github.com/Boehringer-Ingelheim/dso/issues/192
    #  * `watermark` is passed via `--filter` and therefore runs after quarto's own filters
    filter_scripts = {}
    if with_pandocfilter:
        for stage in ["disclaimer", "watermark"]:
            with tempfile.NamedTemporaryFile(delete=False, mode="w") as f:
                f.write("#!/bin/bash\n")
                f.write(f'{sys.executable} -m dso.pandocfilter {stage} "$@"\n')
                filter_scripts[stage] = Path(f.name)
            filter_scripts[stage].chmod(filter_scripts[stage].stat().st_mode | stat.S_IEXEC)

        pandocfilter = f"--filter {filter_scripts['watermark']}"
    else:
        pandocfilter = ""

    # propagate quiet setting to quarto
    quiet = "--quiet" if bool(int(os.environ.get("DSO_QUIET", 0))) else ""
    script = dedent(
        f"""\
        #!/bin/bash
        set -euo pipefail

        # this flags enables building larger reports with embedded resources
        export QUARTO_DENO_V8_OPTIONS=--max-old-space-size=8192

        {before_script}

        quarto render "{quarto_dir}" --execute --output-dir "{report_dir}" {quiet} {pandocfilter}
        """
    )
    try:
        with _pre_ast_filter_in_quarto_config(filter_scripts.get("disclaimer"), quarto_dir):
            res = subprocess.run(script, shell=True, executable="/bin/bash", cwd=cwd)
    finally:
        for filter_script in filter_scripts.values():
            filter_script.unlink()

    if res.returncode:
        sys.exit(res.returncode)


@contextmanager
def _pre_ast_filter_in_quarto_config(filter_script: Path | None, quarto_dir: Path):
    """Context manager that temporarily registers a json filter at the `pre-ast` entry point in `_quarto.yml`"""
    if filter_script is None:
        yield
        return
    config_file = quarto_dir / "_quarto.yml"
    original_config = config_file.read_text() if config_file.exists() else None
    yaml = YAML(typ="safe")
    quarto_config = (yaml.load(original_config) if original_config is not None else None) or {}
    filters = quarto_config.get("filters") or []
    quarto_config["filters"] = [{"path": str(filter_script), "type": "json", "at": "pre-ast"}, *filters]
    yaml.dump(quarto_config, config_file)
    try:
        yield
    finally:
        if original_config is None:
            config_file.unlink()
        else:
            config_file.write_text(original_config)


@contextmanager
def quarto_config_yml(quarto_config: dict | None, quarto_dir: Path):
    """Context manager that temporarily creates a _quarto.yml file and cleans up after itself"""
    if quarto_config is None:
        quarto_config = {}
    config_file = quarto_dir / "_quarto.yml"
    yaml = YAML(typ="safe")
    yaml.dump(quarto_config, config_file)
    try:
        yield
    finally:
        config_file.unlink()
