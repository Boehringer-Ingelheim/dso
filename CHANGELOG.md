# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog][],
and this project adheres to [Semantic Versioning][].

[keep a changelog]: https://keepachangelog.com/en/1.0.0/
[semantic versioning]: https://semver.org/spec/v2.0.0.html

## v0.12.0

### Migration advice

The default pre-commit configuration has been reworked. To update it, navigate to the root of your project. Then run

```bash
rm .pre-commit-config.yaml
dso init .
```

dso init will re-add all files from the project template that are missing from your project. Existing files will not be touched.

### Template updates

-   Update `.pre-commit-config.yaml`, removing unnecessary hooks ([#99](https://github.com/Boehringer-Ingelheim/dso/pull/99)).

### New features

-   Add `dso pull` command, a wrapper around `dso compile-config` + `dvc pull` ([#99](https://github.com/Boehringer-Ingelheim/dso/pull/99))
-   Add templates for Python stages (`quarto_py`, `quarto_ipynb`) ([#98](https://github.com/Boehringer-Ingelheim/dso/pull/98)).

### Documentation

-   Update documentation, finalizing the most important sections of the user guide.

## v0.11.0

### Template updates

-   Single `.gitignore` file per stage. Content of input/output/report folders is ignored. These folders
    do not contain a separate `.gitignore` anymore. This means empty folders won't be tracked by git, but
    this solves issues with dvc refusing to track the output folder because it is already partly tracked by git ([#73](https://github.com/Boehringer-Ingelheim/dso/pull/73)).

### Fixes

-   Do not change the configuration of the root logger, only the `dso` logger. Changing the root logger
    had side-effects on other libraries when importing `dso` in Python ([#80](https://github.com/Boehringer-Ingelheim/dso/pull/80)).

### New features

-   Paths in `params.in.yaml` files declared with `!path` can now be compiled to absolute instead of relative paths ([#78](https://github.com/Boehringer-Ingelheim/dso/pull/78)).
-   Python API that mirrors `dso-r` functionality (e.g. to be used from Jupyter notebooks) ([#30](https://github.com/Boehringer-Ingelheim/dso/pull/30))
-   `dso exec quarto` automatically creates an `output` directory in the stage if it doesn't exist. If it doesn't contain any file,
    it will be removed again after completion ([#73](https://github.com/Boehringer-Ingelheim/dso/pull/73)).

### Documentation

-   Various documentation updates, working towards the first public version of the docs.

### Chore

-   Refactor CLI into separate module ([#30](https://github.com/Boehringer-Ingelheim/dso/pull/30))
-   Defer imports in CLI until they are actually needed to speed up CLI ([#30](https://github.com/Boehringer-Ingelheim/dso/pull/30))
-   Make all modules explicitly private that are not part of the public API ([#30](https://github.com/Boehringer-Ingelheim/dso/pull/30))
-   Relicense the package as LGPL-3.0-or-later, with a more permissive exception for the templates ([#76](https://github.com/Boehringer-Ingelheim/dso/pull/76))

## v0.10.1

### Fixes

-   Take comments into account when linting for `DSO001` ([#69](https://github.com/Boehringer-Ingelheim/dso/pull/69))
-   Make it possible to override watermarks/disclaimers with a simple `null` ([#69](https://github.com/Boehringer-Ingelheim/dso/pull/69)).
-   Compile _all_ configs on `dso repro`, not just the ones relvant to the specified stage. This is required because we don't
    know which other stages dvc might compile ([#69](https://github.com/Boehringer-Ingelheim/dso/pull/69)).
-   Make `get-config` compatible with dvc matrix stages ([#69](https://github.com/Boehringer-Ingelheim/dso/pull/69)).

### Template updates

-   Do not ignore the `.gitignore` files in output/report directories of template ([#63](https://github.com/Boehringer-Ingelheim/dso/pull/63))
-   Update `.pre-commit-config.yaml` for pre-commit 4.x ([#63](https://github.com/Boehringer-Ingelheim/dso/pull/63))

## v0.10.0

### Template updates

-   Improve instruction text in quarto template to get users started more quickly ([#40](https://github.com/Boehringer-Ingelheim/dso/pull/40))
-   Add `.gitignore` catch-all clauses for `output` and `report` folders in stages to not pick up data and repots being tracked via git ([#46](https://github.com/Boehringer-Ingelheim/dso/issues/46)).
-   Every dso project is now also a [uv project](https://docs.astral.sh/uv/concepts/projects/#building-projects) declaring Python dependencies in `pyproject.toml`. This makes it possible to
    use a different dso version per project and makes it easy to work with virtual Python environments ([#52](https://github.com/Boehringer-Ingelheim/dso/pull/52))
-   bash templates now include `-euo pipefail` settings, ensuring that stages fail early and return a nonzero error code if something failed ([#59](https://github.com/Boehringer-Ingelheim/dso/pull/59)).

### Fixes

-   Remove vendored `hiyapyco` code since required changes were released upstream in v0.7.0 ([#45](https://github.com/Boehringer-Ingelheim/dso/pull/45)).
-   `None` values in `params.in.yaml` can now be used to override anything, e.g. to disable watermarking only in a specific stage ([#45](https://github.com/Boehringer-Ingelheim/dso/pull/45)).
-   Clean up existing `*.rmarkdown` files in quarto stage before running `quarto render`. This fixes issues with re-running quarto stages that failed in the previous attempt ([#57](https://github.com/Boehringer-Ingelheim/dso/pull/57)).
-   DSO now respects a `DSO_SKIP_CHECK_ASK_PRE_COMMIT` environment variable. If it is set
    to anything that evaluates as `True`, we skip the check if pre-commit is installed. This was a
    requirement introduced by the R API package, see [#50](https://github.com/Boehringer-Ingelheim/dso/issues/50) ([#58](https://github.com/Boehringer-Ingelheim/dso/pull/58)).
-   Improve logging for "missing path" warning during `compile-config` ([#59](https://github.com/Boehringer-Ingelheim/dso/pull/59)).
-   Improve logging for missing parameters in `dvc.yaml` during `get-config` ([#59](https://github.com/Boehringer-Ingelheim/dso/pull/59)).
-   Make sure internal calls to the dso pandocfilter use the same python and dso version as the parent command. This is important for the upcoming `dso-mgr` feature ([#61](https://github.com/Boehringer-Ingelheim/dso/pull/61)).

## v0.9.0

### New Features

-   `dso watermark` now supports files in PDF format. With this change, quarto reports using the watermark feature can
    be rendered to PDF, too ([#26](https://github.com/Boehringer-Ingelheim/dso/pull/26)).

### Fixes

-   Fix linting rule DSO001: It is now allowed to specify additional arguments in `read_params()`, e.g. `quiet = TRUE` ([#36](https://github.com/Boehringer-Ingelheim/dso/pull/36)).
-   It is now possible to use Jinja2 interpolation in combination with `!path` objects ([#36](https://github.com/Boehringer-Ingelheim/dso/pull/36))
-   Improve error messages when `dso get-config` can't find required input files ([#36](https://github.com/Boehringer-Ingelheim/dso/pull/36))

### Documentation

-   Documentation is now built via sphinx and hosted on GitHub pages: https://boehringer-ingelheim.github.io/dso/ ([#35](https://github.com/Boehringer-Ingelheim/dso/pull/35)).

### Template updates

-   Make instruction comments in quarto template more descriptive ([#33](https://github.com/Boehringer-Ingelheim/dso/pull/33)).
-   Include `params.yaml` in default project `.gitignore`. We decided to not track `params.yaml` in git anymore
    since it adds noise during code review and led to merge conflicts in some cases. In the future, a certain
    `dso` version will be tied to each project, improving reproducibility also without `params.yaml` files.

### Migration advice

-   Add `params.yaml` to your project-level `.gitignore`. Then execute `find -iname "params.yaml" -exec git rm --cached {} \;`
    to untrack existing `params.yaml` files.

## v0.8.2

### Fixes

-   Fixed params.yaml sorting issue - params.yaml order will be kept intact when using `dso get-config`

## v0.8.1

### Fixes

-   Fixed and issue with spaces in image filenames when watermarking a quarto document

## v0.8.0

### New Features

-   `dso init` and `dso create folder` now also work in existing directories. In such case missing files will be added
    from the template, but existing files are never overwritten.
-   There's now a template for a bash stage available in `dso create stage`. The stage template needs can be specified
    via the `--template` flag, otherwise the user is prompted to choose a template.
-   `dso` now has flags to control logging verbosity. The default log-level is `info`. `-q` will set it to `warning`,
    `-qq` to `error` and `-v` to `debug`. The "quiet" option can also be activated by setting the environment variable
    `DSO_QUIET=1` or `DSO_QUIET=2`.
-   `dso exec` and `dso get-config` now have a `--skip-compile` flag to disable automatic internal calls to
    `dso compile-config`. The flag can also be activated by setting the environment variable `DSO_SKIP_COMPILE=1`.

### Fixes

-   Fix that compile-config also compiles parents when in a directory without a `params.in.yaml` file.
-   The order of dictionaries is now preserved by `dso get-config`.
-   When running `dso init` or `dso create`, `dso compile-config` is now only executed
    after it was clearly communicated with the user that the project/stage/folder was successfully created.
-   Specifying a stylesheet using `css` via `dso.quarto` is now possible.
-   Adjusted the log level of some messages to more reasonable defaults. Some messages that were previously `info`
    messages are now `debug` messages and not shown by default.
-   When running `dso repro`, configuration is only compiled once and not recompiled when `dso exec` or `dso get-config`
    is called internally. This reduces runtime and redundant log messages.

## v0.7.0

-   Improved watermarking support

    -   Added test cases for watermarking and the pandocfilter
    -   Support for SVG images
    -   There's now a `dso watermark` command line interface to watermark specified image files. In the future this
        can be used to provide a custom plotting device in R that performs the watermarking.
    -   Changed the watermark layout to use a tiled pattern which is less obstrusive and is guaranteed to cover the entire plot
    -   The watermark is now fully configurable via `params.in.yaml`:

        ```yaml
        dso:
            quarto:
                watermark:
                    text: WATERMARK
                    # change the visuals - Usually fine to stick with the default, but these are the options that can be changed
                    tile_size: [100, 100]
                    font_size: 12
                    font_outline: 2
                    font_color: black
                    font_outline_color: "#AA111160"
        ```

-   Fix issue where dso was stuck in an infinity loop while searching for a config file. Now it should fail
    if it can't be found. To realize this the funcitonality for searching parent folders for a certain file
    that was used in different places was refactored into a separate function.

## v0.6.1

-   Fix issue in `dso get-config` if multiple parameters have been used in a single line in `deps:`.

## v0.6.0

-   Add a `dso lint` command that performs consistency checks on dso projects. For now, only a single rule is
    implemented, but it can be easily extended. The rule:
    -   `DSO001`: In a quarto stage, ensure `dso::read_params` is called and stage name is correct.
-   Logging information is now printed to STDERR instead of STDOUT
-   Add `dso get-config <STAGE>` which will compile and print the configuration for a given stage to STDOUT.
    Additionally, it filters the output to fields that are specified in `dvc.yaml` which forces the user
    to declare all dependencies in `dvc.yaml`.
-   Add automated watermarking of plots in quarto documents as experimental feature. For now, only png images are supported.
    To enable, add to `params.in.yaml`:

    -   `dso.quarto.watermark`: a text to be shown as watermark.
    -   `dso.quarto.disclaimer.text`: a text to be shown as disclaimer box.
    -   `dso.quarto.disclaimer.title`: title of the disclaimer box.

    The disclaimer box is only shown if both text and title are set.

### Migration advice

-   Update `dso-r` to v0.3.0 to take advantage of `dso get-config`.

-   Add the following rule to your `.pre-commit-config.yaml`:
    ```yaml
      - repo: local
          hooks:
          [...]
          - id: lint
              name: Run dso lint
              entry: dso lint --skip-compile
              language: system
              stages: [commit]
    ```

## v0.5.0

-   `dso.before_script` is now `dso.quarto.before_script`. This change has been made because different "exec" modules
    will likely need different setup-scripts (i.e. environment modules). If the script shall be shared nevertheless,
    this can be done with jinja templating.
-   It is now possible to specify bibliography files in `params.in.config:dso.quarto.bibliography` using `!path`.
-   Upon `dso repro`, the CLI asks once if the user wants to install the pre-commit hooks

### Migration advice

-   Move `dso.before_script` to `dso.quarto.before_script` in all your config files.
-   Update all quarto stages to depend only on `params:dso.quarto` instead of `params:dso`. This will avoid
    invalidating the cache unnecessarily.
-   add `/.dso.json` to your .gitignore file

## v0.4.4

-   Remove confirmation before overwriting a newer `params.yaml` file - It turned out not to work well with
    switching branches in git and led to way too many unnecessary questions.
-   Do not fail when `dso.quarto` is `null` in `params.in.yaml` (not all cases were addressed in v0.4.3)

## v0.4.3

-   Fix confirmation to overwrite params.yaml
-   Improve error message when `dso exec quarto` fails
-   Make pre-commit hooks verbose
-   Do not fail when `dso.quarto` is `null` in `params.in.yaml`

## v0.4.2

-   Update quarto template to include `dso` params as dependency
-   Reduce the number of false-positives when asking for confirmation to overwrite params.yaml

## v0.4.1

-   Allow a tolerance of 1s when comparing timestamps of params.in.yaml and params.yaml

## v0.4.0

-   Ask for confirmation before overwriting a newer `params.yaml` file
-   The log messages when compiling configuration files have improved
-   Added `dso exec quarto`, a convenient wrapper to execute quarto stages
    -   Quarto configuration/headers will be read from `params.yaml:qso.quarto`
    -   A shell snippet specified in `params.yaml:dso.before_script` will be executed before rendering the report.
        This is useful for setting up the environment, e.g. by loading modules

## v0.3.1

-   Update quarto template to be concordant with latest dso-r version

## v0.3.0

-   Updated quarto template to use dso code to load files
-   `dso compile-config` now optionally supports specifying a list of paths
-   Renamed `dso create project` to `dso init`
-   Added `dso create folder` in addition to `dso create stage`.
-   Currently only one template for `dso init`, `dso create folder` and `dso create stage` but prepared the project
    to easily support multiple templates in the future
-   Improved pre-commit config. Install it using `pre-commit install` in the project. It automatically performs some
    consistency checks and dvc pull/push/checkout.

## v0.2.0

-   It's now possible to specify paths via the `!path` tag in params.in.yaml. These paths will be checked for existence
    and automatically resolved such that they are always relative to the compiled params.yaml files.

## v0.1.0

-   initial prototype
-   `dso create` command
