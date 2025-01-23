# Configuration

This section provides and overview of dso settings and how to apply them.
Please refer to [DVC configuration](https://dvc.org/doc/user-guide/project-structure/configuration#dvc-configuration) for dvc settings.

## Environment variables

The following environment variables can be used to change certain dso behaviors, independent of the project.

| variable                        | purpose                                                                                                                                           |
| ------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| `DSO_SKIP_CHECK_ASK_PRE_COMMIT` | If set to any non-empty value, dso does not ask whether to install the pre-commit hooks for in a project.                                         |
| `DSO_QUIET`                     | `DSO_QUIET=1` disables info messages, `DSO_QUIET=2` disables warnings. This is equivalent to `-q` and `-qq`, respectively.                        |
| `DSO_VERBOSE`                   | `DSO_VERBOSE=1` enables debug logging. This is equivalent to `-v`                                                                                 |
| `DSO_SKIP_COMPILE`              | `DSO_SKIP_COMPILE` disables automated internal calls to `dso compile-config` in commands that support it. This is equivalent to `--skip-compile`. |

## Project-specific settings -- `pyproject.toml`

Project-specific dso settings can be set in the `pyproject.toml` file at the root of each project in the
`[tool.dso]` section. As the `pyproject.toml` file is tracked by git, these changes affect all users who
collaborate on the project.

```toml
[tool.dso]
# whether to compile relative paths declared with `!path` into absolute paths or
# relative paths (relative to each stage). Defaults to `true`.
use_relative_path = true
```

## Project and user specific settings -- `.dso.json`

For project-specific settings that are not intended to be shared across collaborators. This file is stored
at the root of each project. It is not meant to be edited by hand, but will be created and modified by the `dso` CLI as appropriate.

It currently tracks the following properties:

| variable               | purpose                                                                                                                        |
| ---------------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| `check_ask_pre_commit` | If the user answered "no" to the question if they want to install pre-commit hooks in this project, this will be tracked here. |
