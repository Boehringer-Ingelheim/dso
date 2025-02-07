# DSO: data science operations

_DSO_ is a command line helper for building reproducible data anlaysis projects with ease by connecting our favorite tools:
It builds on top of git and [dvc](https://github.com/iterative/dvc) for code and data versioning and provides project
templates, dependency management via [uv](https://docs.astral.sh/uv), linting checks, hierarchical overlay of configuration files and integrates with quarto and jupyter notebooks.

At Boehringer Ingelheim, we introduced DSO to meet the high quality standards required for biomarker analysis
in clinical trials. DSO is under active development and we value community feedback.

<!-- use absolute URL to make this work also on PyPI -->

| <img src="https://raw.githubusercontent.com/Boehringer-Ingelheim/dso/refs/heads/main/img/dso_kraken.jpg" alt="DSO Kraken" width="700"> | <img src="https://raw.githubusercontent.com/Boehringer-Ingelheim/dso/refs/heads/main/img/dso_tools.png" alt="tools used by DSO"> |
| -------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------- |

## Getting started

Please refer to the [documentation](https://boehringer-ingelheim.github.io/dso), in particular the [getting started](https://boehringer-ingelheim.github.io/dso/getting_started.html) section.

## Installation

See [installation](https://boehringer-ingelheim.github.io/dso/cli_installation.html).

## Contact

Please use the [issue tracker](https://github.com/Boehringer-Ingelheim/dso/issues).

## Release notes

See the [changelog](./CHANGELOG.md).

## License

This program is free software: you can redistribute it and/or modify it under the terms of the GNU Lesser General Public License (LGPL) as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

Additionally, the templates files used internally by `dso init` and `dso create` are distributed under the Creative Commons Zero v1.0
Universal license. See also the [separate LICENSE file](https://github.com/Boehringer-Ingelheim/dso/blob/main/src/dso/templates/LICENSE) in the `templates` directory.

## Credits

dso was initially developed by

-   [Gregor Sturm](https://github.com/grst)
-   [Tom Schwarzl](https://github.com/tschwarzl)
-   [Daniel Schreyer](https://github.com/dschreyer)
-   [Alexander Peltzer](https://github.com/apeltzer)

DSO depends on many great open source projects, most notably [dvc](https://github.com/iterative/dvc), [hiyapyco](https://github.com/zerwes/hiyapyco) and [jinja2](https://jinja.palletsprojects.com/).
