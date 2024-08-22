import os
import subprocess
import sys
from pathlib import Path

import rich_click as click

from dso._logging import log
from dso._util import check_ask_pre_commit
from dso.compile_config import compile_all_configs


@click.command(
    name="repro",
    context_settings={"ignore_unknown_options": True},
)
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
def cli(args):
    """Wrapper around dvc repro, compiling configuration before running."""
    check_ask_pre_commit(Path.cwd())
    compile_all_configs([Path.cwd()])
    os.environ["DSO_SKIP_COMPILE"] = "1"
    cmd = ["dvc", "repro", *args]
    log.info(f"Running `{' '.join(cmd)}`")
    res = subprocess.run(cmd)
    sys.exit(res.returncode)
