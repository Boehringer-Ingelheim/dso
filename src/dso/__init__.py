import logging
import os

import rich_click as click

from ._logging import log
from ._metadata import __version__
from .compile_config import cli as compile_config_cli
from .create import cli as create_cli
from .exec import cli as exec_cli
from .get_config import cli as get_config_cli
from .init import cli as init_cli
from .lint import cli as lint_cli
from .repro import cli as repro_cli
from .watermark import cli as watermark_cli

click.rich_click.USE_MARKDOWN = True


@click.group()
@click.option(
    "-q",
    "--quiet",
    count=True,
    help=(
        "Reduce verbosity. `-q` disables info messages, `-qq` disables warnings. Errors messages cannot be disabled. "
        "The same can be achieved by setting the env var `DSO_QUIET=1` or `DSO_QUIET=2`, respectively."
    ),
    default=int(os.environ.get("DSO_QUIET", 0)),
)
@click.option(
    "-v",
    "--verbose",
    help=(
        "Increase logging verbosity to include debug messages. "
        "The same can be achieved by setting the env var `DSO_VERBOSE=1`."
    ),
    default=bool(int(os.environ.get("DSO_VERBOSE", 0))),
    is_flag=True,
)
@click.version_option(version=__version__, prog_name="dso")
def cli(quiet: int, verbose: bool):
    """Root command"""
    if quiet >= 2:
        log.setLevel(logging.ERROR)
        os.environ["DSO_QUIET"] = "2"
    elif quiet == 1:
        log.setLevel(logging.WARNING)
        os.environ["DSO_QUIET"] = "1"
    elif verbose:
        log.setLevel(logging.DEBUG)
        os.environ["DSO_VERBOSE"] = "1"


cli.add_command(create_cli)
cli.add_command(init_cli)
cli.add_command(compile_config_cli)
cli.add_command(repro_cli)
cli.add_command(exec_cli)
cli.add_command(lint_cli)
cli.add_command(get_config_cli)
cli.add_command(watermark_cli)
