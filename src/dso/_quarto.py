"""Helper functions for rendering quarto documents"""

import os
import stat
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from importlib import resources
from pathlib import Path
from textwrap import dedent, indent

from ruamel.yaml import YAML

from dso import assets


def render_quarto(
    quarto_dir: Path,
    report_dir: Path,
    before_script: str,
    cwd: Path,
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

    # propagate quiet setting to quarto
    quiet = "--quiet" if bool(int(os.environ.get("DSO_QUIET", 0))) else ""
    script = dedent(
        f"""\
        #!/bin/bash
        set -euo pipefail

        # this flags enables building larger reports with embedded resources
        export QUARTO_DENO_V8_OPTIONS=--max-old-space-size=8192

        {before_script}

        quarto render "{quarto_dir}" --execute --output-dir "{report_dir}" {quiet}
        """
    )
    res = subprocess.run(script, shell=True, executable="/bin/bash", cwd=cwd)

    if res.returncode:
        sys.exit(res.returncode)


@contextmanager
def quarto_config_yml(quarto_config: dict | None, quarto_dir: Path):
    """
    Context manager that temporarily creates a _quarto.yml file and cleans up after itself

    Registers DSO's filters in `_quarto.yml` if the corresponding options are set:
     * `disclaimer`: lua filter that adds the disclaimer as a quarto callout. It runs at the `pre-ast` entry point,
       such that quarto renders the callout in all output formats (e.g. PDF).
     * `watermark`: pandoc filter that adds watermarks to images and plotly plots. It runs at the `post-quarto`
       entry point, as otherwise quarto would rewrite the paths of the (temporary) watermarked images.
    """
    quarto_config = dict(quarto_config) if quarto_config is not None else {}
    filters = list(quarto_config.get("filters") or [])
    if quarto_config.get("disclaimer"):
        filters.append({"path": str(resources.files(assets) / "disclaimer.lua"), "at": "pre-ast"})

    # The watermark filter is a temporary script that calls the current python binary with the dso.pandocfilter
    # module. This may seem cumbersome, but we do it this way because
    #  * pandoc only supports a single binary for a filter, referring to subcommands or `-m` is not possible here
    #  * we want to ensure that exactly the same python/dso version is used for the pandocfilter as for the
    #    parent command (important when running dso from a venv)
    filter_script = None
    if quarto_config.get("watermark"):
        with tempfile.NamedTemporaryFile(delete=False, mode="w") as f:
            f.write("#!/bin/bash\n")
            f.write(f'{sys.executable} -m dso.pandocfilter "$@"\n')
            filter_script = Path(f.name)
        filter_script.chmod(filter_script.stat().st_mode | stat.S_IEXEC)
        filters.append({"path": str(filter_script), "type": "json", "at": "post-quarto"})

    if filters:
        quarto_config["filters"] = filters
    config_file = quarto_dir / "_quarto.yml"
    yaml = YAML(typ="safe")
    yaml.dump(quarto_config, config_file)
    try:
        yield
    finally:
        config_file.unlink()
        if filter_script is not None:
            filter_script.unlink()
