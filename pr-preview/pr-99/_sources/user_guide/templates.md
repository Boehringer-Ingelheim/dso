# Project and stage templates

DSO provides a templating engine that allows to [quickly boostrap a project](../getting_started.md#dso-init----initialize-a-project)
(`dso init`), folder, or stages (`dso create`).
Templates are based on [jinja2](https://jinja.palletsprojects.com/en/stable/templates/).

## Available templates

DSO currently comes with the following templates:

Project templates:

-   [default](https://github.com/Boehringer-Ingelheim/dso/tree/main/src/dso/templates/init/default) - Default template, with
    integration of `git`, `dvc`, `uv`, `pre-commit`, and `editorconfig`.

Folder templates:

-   [default](https://github.com/Boehringer-Ingelheim/dso/tree/main/src/dso/templates/folder/default) - This one is very minimal, just a folder with `dvc.yaml` and `params.in.yaml` files.

Stage templates:

-   [quarto_r](https://github.com/Boehringer-Ingelheim/dso/tree/main/src/dso/templates/stage/quarto) - Template for quarto notebook in R
-   [quarto_py](https://github.com/Boehringer-Ingelheim/dso/tree/main/src/dso/templates/stage/quarto) - Template for quarto notebook in Python (quarto markdown (`.qmd`) format)
-   [quarto_r](https://github.com/Boehringer-Ingelheim/dso/tree/main/src/dso/templates/stage/quarto) - Template for quarto notebook in Python (jupyter notebook (`.ipynb`) format)
-   [bash](https://github.com/Boehringer-Ingelheim/dso/tree/main/src/dso/templates/stage/bash) - Template for executing a bash snippet

The source code of the templates can be [inspected on GitHub](https://github.com/Boehringer-Ingelheim/dso/tree/main/src/dso/templates).
Templates shipped with DSO are [licensed](https://github.com/Boehringer-Ingelheim/dso/blob/main/src/dso/templates/LICENSE) under the Creative Commons Zero v1.0
Universal license.

## Using custom template libraries

Currently, dso only supports the internal templates mentioned above. However, we plan to add support to custom
stage templates soon ([#9](https://github.com/Boehringer-Ingelheim/dso/issues/9)). This enables some interesting use-cases:

-   Organization-specific templates: Use templates that make it easier to comply with internal processes or apply
    corporate design.
-   Best-practice codebases: Start off common analysis types off a predefined template. We believe that some analyses
    require more flexibility than predefined worflows such as nf-core, but can still benefit from a structured
    "base" document to get started with.

## Writing templates

Template directories are recursively copied to their destination and files are rendered with [jinja2](https://jinja.palletsprojects.com/en/stable/templates/).
You can use all features of jinja2 such as `if/else` blocks or loops. Additionally, you have access to the
following variables:

Available variables for **project** templates:

| variable            | content                                               |
| ------------------- | ----------------------------------------------------- |
| project_name        | project/folder name as provided to the `dso init` CLI |
| project_description | description as provided to the `dso init` CLI         |

Available variables for **folder** templates:

| variable    | content                                                |
| ----------- | ------------------------------------------------------ |
| folder_name | folder name as provided to the `dso create folder` CLI |

Available variables for **stage** templates:

| variable          | content                                               |
| ----------------- | ----------------------------------------------------- |
| stage_name        | folder name as provided to the `dso create stage` CLI |
| stage_description | description as provided to the `dso create stage` CLI |
| stage_path        | Path to the stage relative to the project root        |
