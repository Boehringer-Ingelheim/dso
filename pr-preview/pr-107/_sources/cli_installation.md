# Installation

The DSO CLI is available [from PyPI](https://pypi.org/project/dso-core/). The package is named `dso-core`
You can think of it as the "core" package of DSO, while there is also a [separate R package](https://github.com/Boehringer-Ingelheim/dso-r)
and there might be other "extension" packages in the future.

We recommend installing the DSO CLI in an isolated environment using, e.g., [uv](https://docs.astral.sh/uv/) or [pipx](https://pipx.pypa.io/latest/installation/).

```bash
uv tool install dso-core
```

This command installs the `dso` binary:

```{eval-rst}
.. click:run::
    from dso.cli import dso
    invoke(dso, args=["--version"])
```

If you prefer to manage the Python environment yourself, you can use `pip` as usual:

```bash
pip install dso-core
```

## Freezing the dso version within a project

:::{attention}

This feature is still experimental. In particular, we are still working on the ergonomics,
as remembering to type `uv run dso` every time is not very user-friendly. Once this is
worked out, it will very likely become the default for all dso projects.

See also [dso#3](https://github.com/Boehringer-Ingelheim/dso-mgr/issues/3).
:::

To ensure consistent results between collaborators and that the porject can be reproduced in exactly the
same way in the future, it is good practice to pin a specific version of dso within each project. Since
each dso project is also a [uv project](https://docs.astral.sh/uv/guides/projects/) with dependencies
declared in `pyproject.toml`, this makes it easy freeze the dso version.

By using

```bash
uv run dso
```

instead of

```bash
dso
```

`uv` runs the specified version of `dso` and installes it automatically in the background, if necessary. Running
this command for the first time will create a [`uv.lock`](https://docs.astral.sh/uv/guides/projects/#uvlock) file that
contains the exact information about the project's dependencies.

To update the version of `dso` within the project, you can use

```bash
uv add -U dso_core
```
