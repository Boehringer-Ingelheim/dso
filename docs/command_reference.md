# Command reference

## dso

```{eval-rst}
.. click:run::
    from dso.cli import dso
    invoke(dso, args=["--help"])
```

## dso compile-config

```{eval-rst}
.. click:run::
    from dso.cli import cli as dso
    invoke(dso, args=["compile-config", "--help"])
```

## dso create

```{eval-rst}
.. click:run::
    from dso.cli._create import create_cli
    invoke(create_cli, args=["--help"])
```

### dso create folder

```{eval-rst}
.. click:run::
    from dso.cli._create import create_folder_cli
    invoke(create_folder_cli, args=["--help"])
```

### dso create stage

```{eval-rst}
.. click:run::
    from dso.cli._create import create_stage_cli
    invoke(create_stage_cli, args=["--help"])
```

## dso exec

```{eval-rst}
.. click:run::
    from dso.cli import exec_cli
    invoke(exec_cli, args=["--help"])
```

### dso exec quarto

```{eval-rst}
.. click:run::
    from dso.cli._exec import exec_quarto_cli
    invoke(exec_quarto_cli, args=["--help"])
```

## dso get-config

```{eval-rst}
.. click:run::
    from dso.cli import get_config_cli
    invoke(get_config_cli, args=["--help"])
```

## dso init

```{eval-rst}
.. click:run::
    from dso.cli import init_cli
    invoke(init_cli, args=["--help"])
```

## dso lint

```{eval-rst}
.. click:run::
    from dso.cli import lint_cli
    invoke(lint_cli, args=["--help"])
```

## dso repro

```{eval-rst}
.. click:run::
    from dso.cli import repro_cli
    invoke(repro_cli, args=["--help"])
```

## watermark cli

```{eval-rst}
.. click:run::
    from dso.cli import watermark_cli
    invoke(watermark_cli, args=["--help"])
```
