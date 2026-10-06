# `uv` integration

[`uv`](https://docs.astral.sh/uv/) is an ultrafast python package and project manager. Every dso
project is also a `uv` project, so you can use all the features described in the uv [working with projects](https://docs.astral.sh/uv/guides/projects/)
documentation.

Integration with `uv` serves two main purposes:

-   freeze the version of `dso` per project to ensure reproducibility in the future, even if dso behavior changes.
    This features is a work-in-progress, see also [installation](../cli_installation.md#freezing-the-dso-version-within-a-project).
-   Provide a python virtual environment for all python stages in the project.

Using a separate virtual environment for each project is considered good practice to ensure reproducibility and
to avoid dependency conflicts. `uv` makes this very easy.

To add dependencies, edit the `dependencies` section in `pyproject.toml` or use

```bash
uv add <some_package>
```

to install it.

By using

```bash
uv sync
```

all requested packages are installed into the local `.venv` directory. At the same time a `uv.lock` file
is created that pins the exact versions of each package. This file is tracked by `.git`, which means
every collaborator will get exactly the same environment if they run `uv sync` on their machine.

To run a script within the virtual environment, use

```bash
uv run ./some_script.py
```

All DSO Python stages use the virtual environment by default.
