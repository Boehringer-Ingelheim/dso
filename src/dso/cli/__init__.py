"""Main entry point for CLI"""

import logging
import os
import subprocess
import sys
from json import dump as json_dump
from os import getcwd
from pathlib import Path
from textwrap import dedent

import rich_click as click
from rich.prompt import Confirm
from ruamel.yaml import YAML

from dso._logging import log
from dso._metadata import __version__
from dso._mv import increment_prefixes, mv
from dso._templates import get_instantiate_template_help_text, instantiate_with_repo, prompt_for_template_params
from dso._util import get_project_root

from ._create import dso_create
from ._exec import dso_exec

click.rich_click.USE_MARKDOWN = True


@click.command(name="compile-config")
@click.option(
    "--all",
    is_flag=True,
    type=bool,
    default=False,
    help="Compile all configs in the project",
)
@click.argument("args", nargs=-1)
def dso_compile_config(all, args):
    """Compile params.in.yaml into params.yaml using Jinja2 templating and resolving recursive templates.

    If passing no arguments, configs will be resolved for the current working directory (i.e. all parent configs,
    and all configs in child directories). Alternatively a list of paths can be specified. In that case, all configs
    related to these paths will be compiled (useful for using with pre-commit).
    """
    from dso._compile_config import compile_all_configs

    if all and not len(args):
        paths = [get_project_root(Path.cwd())]
    elif all:
        paths = [get_project_root(Path(x)) for x in args]
    elif not len(args):
        paths = [Path.cwd()]
    else:
        paths = [Path(x) for x in args]

    compile_all_configs(paths)


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
@click.option(
    "--json",
    is_flag=True,
    type=bool,
    default=False,
    help="Output config in json format.",
)
@click.argument(
    "stage",
)
def dso_get_config(stage, all, skip_compile, json):
    """Get the configuration for a given stage and print it to STDOUT in yaml or json format.

    The path to the stage must be relative to the root dir of the project.

    By default, the configuration is filtered to include only the keys that are mentioned in `dvc.yaml` to force
    declaring all dependencies.

    If multiple stages are defined in a single `dvc.yaml`, the stage name MUST be specified using
    `path/to/stage:stage_name` unless `--all` is given.
    """
    from dso._get_config import get_config

    try:
        out_config = get_config(stage, all=all, skip_compile=skip_compile)
        if json:
            json_dump(out_config, sys.stdout, indent=4)  # Output the config in JSON format
        else:
            yaml = YAML()
            yaml.dump(out_config, sys.stdout)  # Output the config in YAML format
    except KeyError as e:
        log.error(f"dvc.yaml defines parameter {e} that is not in params.yaml")
        sys.exit(1)


@click.argument("name", required=False)
@click.option("--library", "-l", "library_id", help="Choose the template library to use")
@click.option(
    "--template", "-t", "template_id", help="Specify the id of a template to use from the specified template library"
)
@click.command(
    "init",
    help=dedent("""\
    If you wish to initialize DSO in an existing project, you can specify an existing directory. In
    this case, it will initialize files from the template that do not exist yet, but never overwrite existing files.\n
    """)
    + get_instantiate_template_help_text("project"),
    context_settings={
        "ignore_unknown_options": True,
        "allow_extra_args": True,
    },
)
@click.pass_context
def dso_init(ctx, name: str | None, *, template_id: str | None = None, library_id: str | None = None):
    """Initialize a new project. A project can contain several stages organized in arbitrary subdirectories."""
    from dso._compile_config import compile_all_configs

    # get extra arguments, see https://stackoverflow.com/questions/32944131/add-unspecified-options-to-cli-command-using-python-click
    params = {ctx.args[i][2:]: ctx.args[i + 1] for i in range(0, len(ctx.args), 2)}
    if name is not None:
        params["name"] = name

    template, params = prompt_for_template_params("init", library_id, template_id, **params)

    target_dir = Path(getcwd()) / params["name"]

    if target_dir.exists():
        if not Confirm.ask("[bold]Directory already exists. Do you want to initialize DSO in an existing project?"):
            sys.exit(1)

    instantiate_with_repo(template["path"], target_dir, **params)
    log.info("[green]Project initalized successfully.")
    compile_all_configs([target_dir])


@click.command(name="lint")
@click.option(
    "--skip-compile",
    help="Do not compile configs before linting. The same can be achieved by setting the `DSO_SKIP_COMPILE=1` env var.",
    type=bool,
    default=bool(int(os.environ.get("DSO_SKIP_COMPILE", 0))),
    is_flag=True,
)
@click.argument("args", nargs=-1)
def dso_lint(args, skip_compile: bool = False):
    """Lint a dso project

    TODO: Linting is currently disabled because of its slow speed with only one rule implemented. See #70, #5, and #66
    on GitHub for more information.

    Performs consistency checks according to a set of rules.

    If passing no arguments, linting will be performed for the current working directory. Alternatively a list of paths
    can be specified. In that case, all stages related to any of the files are linted (useful for using with pre-commit).

    Configurations are compiled before linting.
    """
    # TODO linting is temporarily disabled because it's slow and basically no checks are implemented
    # See #70, #5 and #66
    pass
    # from dso._compile_config import compile_all_configs
    # from dso._lint import lint

    # if not len(args):
    #     paths = [Path.cwd()]
    # else:
    #     paths = [Path(x) for x in args]
    # if not skip_compile:
    #     compile_all_configs(paths)
    # lint(paths)


@click.command(name="watermark")
@click.argument("input_image", type=Path)
@click.argument("output_image", type=Path)
@click.option("--text", help="Text to use as watermark", required=True)
@click.option(
    "--tile_size",
    type=(int, int),
    help="watermark text will be arranged in tile of this size (once at top left, once at middle right). Specify the tile size as e.g. `120 80`",
)
@click.option("--font_size", type=int)
@click.option("--font_outline", type=int)
@click.option("--font_color", help="Use RGBA (e.g. `#AAAAAA88`) to specify transparency")
@click.option("--font_outline_color", help="Use RGBA (e.g. `#AAAAAA88`) to specify transparency")
def dso_watermark(input_image, output_image, text, **kwargs):
    """Add a watermark to an image

    To be called from the dso-r package for implementing a custom graphics device.
    Can also be used standalone for watermarking images.
    """
    kwargs = {k: v for k, v in kwargs.items() if v is not None}

    from dso._watermark import Watermarker

    Watermarker.add_watermark(input_image, output_image, text=text, **kwargs)


@click.group(invoke_without_command=True)
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
def dso(quiet: int, verbose: bool):
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


def _dvc_wrapper(command: str):
    @click.command(
        name=command,
        help=f"Wrapper around `dvc {command}`, compiling configuration before running.",
        context_settings={"ignore_unknown_options": True},
    )
    @click.argument("args", nargs=-1, type=click.UNPROCESSED)
    def command_wrapper(args):
        """Wrapper around any dvc command, compiling configuration before running."""
        from dso._compile_config import compile_all_configs
        from dso._util import check_ask_pre_commit

        check_ask_pre_commit(Path.cwd())
        compile_all_configs([get_project_root(Path.cwd())])
        os.environ["DSO_SKIP_COMPILE"] = "1"
        # use `python -m dvc`` syntax to ensure we are using dvc from the same venv
        cmd = [sys.executable, "-m", "dvc", command, *args]
        log.debug(f"Running `{' '.join(cmd)}`")
        res = subprocess.run(cmd)
        sys.exit(res.returncode)

    return command_wrapper


@click.command(name="mv")
@click.argument(
    "source",
    type=click.Path(exists=True, file_okay=True, dir_okay=True, path_type=Path),
)
@click.argument(
    "target",
    type=click.Path(file_okay=True, dir_okay=True, path_type=Path),
    required=False,
)
@click.option(
    "--increment-prefix",
    help=("Increments the prefix for source stage or folder and subsequent items."),
    default=None,
)
def dso_mv(source: Path, target: Path | None, increment_prefix: str | None):
    """
    Move or rename a stage or a folder and update references to it (experimental).

    This command allows you to move or rename a stage or folder within your project. It ensures that all references
    to the moved or renamed stage or folder are updated in associated files such as `dvc.yaml`, `params.in.yaml`,
    and source files. Note that this feature is experimental, and references inside the target will not be updated automatically.
    These must be adjusted manually.

    `mv` also has functionality to increment an index in the stage or folder prefixes. For this, one has to
    provide along with the source argument the option `--increment-prefix`, the prefix index for the specified stage
    or folder and all subsequent items will be incremented automatically using `dso mv` or renamed if they are not dso items
    (do not contain dvc.yaml files).
    An example would be `dso mv 01_preprocessing --increment-prefix 02`, then it would be renamed to
    02_preprocessing, 02_analysis would be renamed to 03_analysis, and so on. Prefixes can contain a variable stem and
    a numeric part. e.g. A0101, A0102, A0103, ..  or 1235-923-01, 1235-923-02, 1235-923-03,...

    You must specify either a target path or the `--increment-prefix` option, but not both. These options are mutually exclusive.
    """
    if (target is None and increment_prefix is None) or (target is not None and increment_prefix is not None):
        log.error("Either target or increment need to be specified, but not both.")
        sys.exit(1)
    elif target is not None and increment_prefix is None:
        mv(source, target)
    elif target is None and increment_prefix is not None:
        increment_prefixes(source, increment_prefix)
    else:
        log.error(f"Invalid state reached with: target '{target}' and increment_prefix '{increment_prefix}'.")
        sys.exit(1)


dso.add_command(dso_create)
dso.add_command(dso_init)
dso.add_command(dso_compile_config)
dso.add_command(dso_exec)
dso.add_command(dso_lint)
dso.add_command(dso_get_config)
dso.add_command(dso_watermark)
dso.add_command(dso_mv)

for command in ["repro", "pull", "status", "push"]:
    dso.add_command(_dvc_wrapper(command))
