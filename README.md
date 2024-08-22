# DSO: data science operations

<img src="img/dso_kraken.jpg" alt="DSO Kraken" width="250" />

*DSO* is a command line helper for building reproducible data anlaysis projects with ease.
It builds on top of [dvc](https://github.com/iterative/dvc) for data versioning and provides project
templates, linting checks, hierarchical overlay of configuration files and integrates with quarto and jupyter notebooks.

At Boehringer Ingelheim, we introduced DSO to meet the high quality standards required for biomarker analysis
in clinical trials. DSO is still under early development and we value community feedback.

## Getting started

### What is DVC?
[DVC](https://github.com/iterative/dvc) is like "git for data". It can version large data files and data directories alongside source code tracked with git. In addition to versioning files, dvc can be used to run analyses in a reproducible way by declaring input and output files as well as commands to be executed in a `dvc.yaml` configuration file. After executing an analysis, timestamps and checksums of all input and output files are stored in a `lock` file, providing a provenance record. Different analysis tasks are organized in *stages*. Since input and output files of each stage are declared, dvc can build a dependency graph of the stages to re-execute stages as appropriate if input data or preprocessing steps have been updated.

### Creating a project from a template
There are three types of DSO templates: project, folders and stages. A *project* is the root of your project
and always a git repository at the same time. It can be created using `dso init`. A *stage* is an executable
step of your analysis (usually one script with defined inputs and outputs) organized in a folder. Stages
cannot be nested. A *folder* is used to organize stages in a hierarchical way within the project.

You can use `dso init` to create a new project
```
Usage: dso init [OPTIONS] [NAME]

 Initialize a new project. A project can contain several stages organized in arbitrary subdirectories.
 If you wish to initialize DSO in an existing project, you can specify an existing directory. In this case, it will
 initialize files from the template that do not exist yet, but never overwrite existing files.

╭─ Options ────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --description    TEXT                                                                                            │
│ --help                 Show this message and exit.                                                               │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```

Within a project, you can use `dso create` to initalize folders and stages from a predefined template

```

 Usage: dso create [OPTIONS] COMMAND [ARGS]...

 Create stage folder structure subcommand.

╭─ Options ────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --help      Show this message and exit.                                                                          │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ folder  Create a new folder. A folder can contain subfolders or stages.                                          │
│ stage   Create a new stage.                                                                                      │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```

## Installation

DSO requires Python 3.10 or later.

You can install it with pip using

```bash
pip install git+https://github.com/Boehringer-Ingelheim/dso.git@main
```

The tool will be made available on PyPI in the near future.

## Release notes

See the [changelog](./CHANGELOG.md).
