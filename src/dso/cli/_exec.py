import os
from pathlib import Path

import rich_click as click
from ruamel.yaml import YAML

from dso._logging import log
from dso._util import add_directory


@click.command("quarto")
@click.argument("stage", required=True)
@click.option(
    "--skip-compile",
    help="Do not compile configs before linting. The same can be achieved by setting the `DSO_SKIP_COMPILE=1` env var.",
    type=bool,
    default=bool(int(os.environ.get("DSO_SKIP_COMPILE", 0))),
    is_flag=True,
)
def dso_exec_quarto(stage: str, skip_compile: bool = True):
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
    from dso._compile_config import compile_all_configs
    from dso._quarto import quarto_config_yml, render_quarto

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

    with add_directory(stage_dir / "output"):
        with quarto_config_yml(quarto_config, stage_dir / "src"):
            render_quarto(
                stage_dir / "src",
                report_dir=stage_dir / "report",
                before_script=before_script,
                cwd=stage_dir,
                with_pandocfilter="watermark" in quarto_config or "disclaimer" in quarto_config,
            )


@click.group(name="exec")
def dso_exec():
    """Dso wrappers around various tools"""
    pass


dso_exec.add_command(dso_exec_quarto)
