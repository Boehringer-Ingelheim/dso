import os
import stat
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path
from textwrap import dedent, indent

import rich_click as click
from ruamel.yaml import YAML

from dso.compile_config import compile_all_configs

from ._logging import log


def _render_quarto(quarto_dir: Path, report_dir: Path, before_script: str, cwd: Path, with_pandocfilter: bool = False):
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

        quarto render "{quarto_dir}" --output-dir "{report_dir}" {quiet} {pandocfilter}
        """
    )
    res = subprocess.run(script, shell=True, executable="/bin/bash", cwd=cwd)

    # clean up
    if filter_script is not None:
        filter_script.unlink()

    if res.returncode:
        sys.exit(res.returncode)


@contextmanager
def _quarto_config_yml(quarto_config: dict | None, quarto_dir: Path):
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


@click.command("quarto")
@click.argument("stage", required=True)
@click.option(
    "--skip-compile",
    help="Do not compile configs before linting. The same can be achieved by setting the `DSO_SKIP_COMPILE=1` env var.",
    type=bool,
    default=bool(int(os.environ.get("DSO_SKIP_COMPILE", 0))),
    is_flag=True,
)
def exec_quarto(stage: str, skip_compile: bool = True):
    """
    Render a quarto stage. Quarto parameters are inherited from params.yaml

    A quarto stage is assmed to have the following structure:
     * One or multiple `.qmd` files in `src`
     * Reports will be stored in `report`

    No `_quarto.yml` shall be present as it will be automatically created tempoarily. Instead
    supply quarto parameters in `params.in.yaml` under the key `dso.quarto`.

    Parameters
    ----------
    stage
        Path to the stage, e.g. `.` for the current directory.
    """
    stage_dir = Path(stage).absolute()
    log.info(f"Executing quarto stage {stage_dir}")
    if not skip_compile:
        log.debug("Skipping compilation of config files.")
        compile_all_configs([stage_dir])
        os.environ["DSO_SKIP_COMPILE"] = (
            "1"  # no need to re-compile the config when calling `read_params` in the script
        )
    yaml = YAML(typ="safe")
    params = yaml.load(stage_dir / "params.yaml")
    dso_config = params.get("dso", {})
    if dso_config is None:
        dso_config = {}
    quarto_config = dso_config.get("quarto", {})
    # before script is dso-specific - we retrieve and remove it from the quarto config
    before_script = quarto_config.pop("before_script", "")

    # The following keys in the quarto configuration are paths. They need to be amended by a ".." to compensate
    # for the `src` directory in the quarto stage. I couln't find a comprehensive specification of the
    # _quarto.yml file to find all possible keys that are affected. Let's just grow this list as issues appear.
    QUARTO_PATH_KEYS = ["bibliography", "css"]
    for key in QUARTO_PATH_KEYS:
        try:
            tmp_list = quarto_config[key]
            new_conf = []
            # can be either a str or a list of strs (in case of multiple files). Let's force this to be a list.
            if isinstance(tmp_list, str):
                tmp_list = [tmp_list]
            for tmp_val in tmp_list:
                tmp_path = Path(tmp_val)
                if not tmp_path.is_absolute():
                    tmp_path = ".." / tmp_path
                new_conf.append(str(tmp_path))
            # if only one entry, don't add a list
            quarto_config[key] = new_conf if len(new_conf) > 1 else new_conf[0]
        except KeyError:
            pass

    with _quarto_config_yml(quarto_config, stage_dir / "src"):
        _render_quarto(
            stage_dir / "src",
            report_dir=stage_dir / "report",
            before_script=before_script,
            cwd=stage_dir,
            with_pandocfilter="watermark" in quarto_config or "disclaimer" in quarto_config,
        )


@click.group(name="exec")
def cli():
    """Dso wrappers around various tools"""
    pass


cli.add_command(exec_quarto)
