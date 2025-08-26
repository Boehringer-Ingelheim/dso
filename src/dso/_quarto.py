"""Helper functions for rendering quarto documents"""

import os
import stat
import shutil
import subprocess
import sys
import tempfile
import contextlib
from contextlib import contextmanager
from pathlib import Path
from textwrap import dedent, indent

from ruamel.yaml import YAML


def _make_pandoc_filter_script() -> Path:
    """
    Create a temporary wrapper script that calls: python -m dso.pandocfilter
    Returns the script Path. Caller must delete it.
    """
    if os.name == "nt":
        # Windows: use a .cmd so pandoc can execute it
        fd, script_path = tempfile.mkstemp(suffix=".cmd")
        os.close(fd)
        p = Path(script_path)
        # Quote python path; forward all args
        p.write_text(f'@echo off\r\n"{sys.executable}" -m dso.pandocfilter %*\r\n', encoding="utf-8")
        return p
    else:
        # POSIX: use a .sh and make it executable
        fd, script_path = tempfile.mkstemp(suffix=".sh")
        os.close(fd)
        p = Path(script_path)
        p.write_text(f"#!/bin/bash\n{sys.executable} -m dso.pandocfilter \"$@\"\n", encoding="utf-8")
        p.chmod(p.stat().st_mode | stat.S_IEXEC)
        return p


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
        Bash snippet to execute before running quarto (e.g. to setup the environment)
        (Ignored on Windows)
    """
    quarto_dir = Path(quarto_dir)
    report_dir = Path(report_dir).absolute()
    cwd = Path(cwd)

    report_dir.mkdir(parents=True, exist_ok=True)

    # Clean up leftover .rmarkdown files from previous failed render attempts
    for f in quarto_dir.glob("*.rmarkdown"):
        if f.is_file():
            with contextlib.suppress(OSError):
                f.unlink()

    # Optional pandoc filter wrapper
    filter_script: Path | None = None
    if with_pandocfilter:
        filter_script = _make_pandoc_filter_script()

    # Quiet flag from env (compatible with previous behavior)
    quiet_env = os.environ.get("DSO_QUIET", "0")
    quiet = bool(int(quiet_env)) if quiet_env.isdigit() else False

    # Bump Deno memory for Quarto
    env = os.environ.copy()
    env.setdefault("QUARTO_DENO_V8_OPTIONS", "--max-old-space-size=8192")

    try:
        if os.name == "nt":
            # Windows: call Quarto CLI directly (no /bin/bash)
            quarto = shutil.which("quarto")
            if not quarto:
                raise FileNotFoundError(
                    "Quarto CLI not found on PATH (required on Windows). "
                    "Install Quarto or add it to PATH."
                )

            cmd = [quarto, "render", str(quarto_dir), "--execute", "--output-dir", str(report_dir)]
            if quiet:
                cmd.append("--quiet")
            if filter_script is not None:
                cmd += ["--filter", str(filter_script)]

            subprocess.run(cmd, cwd=str(cwd), env=env, check=True)

        else:
            # POSIX: honor the bash snippet and use /bin/bash
            before_script_indented = indent(before_script or "", " " * 8)
            filter_arg = f"--filter {filter_script}" if filter_script else ""
            quiet_arg = "--quiet" if quiet else ""

            script = dedent(
                f"""\
                #!/bin/bash
                set -euo pipefail

                # this flag enables building larger reports with embedded resources
                export QUARTO_DENO_V8_OPTIONS="${{QUARTO_DENO_V8_OPTIONS:---max-old-space-size=8192}}"

                {before_script_indented}

                quarto render "{quarto_dir}" --execute --output-dir "{report_dir}" {quiet_arg} {filter_arg}
                """
            )
            subprocess.run(script, shell=True, executable="/bin/bash", cwd=str(cwd), env=env, check=True)

    finally:
        if filter_script is not None:
            with contextlib.suppress(OSError):
                filter_script.unlink()


@contextmanager
def quarto_config_yml(quarto_config: dict | None, quarto_dir: Path):
    """Context manager that temporarily creates a _quarto.yml file and cleans up after itself"""
    if quarto_config is None:
        quarto_config = {}
    config_file = Path(quarto_dir) / "_quarto.yml"
    yaml = YAML(typ="safe")
    with config_file.open("w", encoding="utf-8", newline="\n") as fh:
        yaml.dump(quarto_config, fh)
    try:
        yield
    finally:
        with contextlib.suppress(FileNotFoundError, PermissionError):
            config_file.unlink()
