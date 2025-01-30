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


def render_quarto(quarto_dir: Path, report_dir: Path, before_script: str, cwd: Path, with_pandocfilter: bool = False):
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
    before_script = indent(before_script, " " * 8)
    report_dir = report_dir.absolute()
    report_dir.mkdir(exist_ok=True)

    # clean up existing `.rmarkdown` files that may interfere with rendering
    # these are leftovers from a previous, failed `quarto render` attempt. If they still exist, the next attempt
    # fails. We remove them *before* the run instead of cleaning them up *after* the run, because they
    # may be usefule for debugging failures.
    # see https://github.com/Boehringer-Ingelheim/dso/issues/54
    for f in quarto_dir.glob("*.rmarkdown"):
        if f.is_file():
            f.unlink()

    # Enable pandocfilter if requested.
    # We create a temporary script that then calls the current python binary with the dso.pandocfilter module
    # This may seem cumbersome, but we do it this way because
    #  * pandoc only supports a single binary for `--filter`, referring to subcommands or `-m` is not possible here
    #  * we want to ensure that exactly the same python/dso version is used for the pandocfilter as for the
    #    parent command (important when running through dso-mgr)
    filter_script = None
    if with_pandocfilter:
        with tempfile.NamedTemporaryFile(delete=False, mode="w") as f:
            f.write("#!/bin/bash\n")
            f.write(f'{sys.executable} -m dso.pandocfilter "$@"\n')
            filter_script = Path(f.name)

        filter_script.chmod(filter_script.stat().st_mode | stat.S_IEXEC)

        pandocfilter = f"--filter {filter_script}"
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
    res = subprocess.run(script, shell=True, executable="/bin/bash", cwd=cwd)

    # clean up
    if filter_script is not None:
        filter_script.unlink()

    if res.returncode:
        sys.exit(res.returncode)


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
