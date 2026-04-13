# Project and stage templates

DSO provides a templating engine that allows to [quickly boostrap a project](../tutorials/getting_started.md#dso-init----initialize-a-project)
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

DSO templates are organized in "template libraries". The "default" template library ships with the DSO package.
Additionally, custom template libraries can be specified using the [`DSO_TEMPLATE_LIBRARIES` environment variable](cli_configuration.md#environment-variables).
This enables the following use-cases:

-   Organization-specific templates: Use templates that make it easier to comply with internal processes or apply
    corporate design.
-   Best-practice codebases: Start off common analysis types off a predefined template. We believe that some analyses
    require more flexibility than predefined worflows such as nf-core, but can still benefit from a structured
    "base" document to get started with.

Template libraries can be provided as:

-   A python module (for instance, the default library is `dso.templates`)
-   A path on the file system (e.g. `/data/share/dso_templates`)

A template library is structured as follows:

```
.
├── folder
│   ├── folder_template_1
│   └── folder_template_2
├── index.json
├── init
│   └── project_template_1
└── stage
    ├── stage_template_1
    └── stage_template_2
```

The subfolders `init`, `folder` and `stage` contain templates for the `dso init`, `dso create folder` and `dso create stage`
commands, respectively. Each template is organized in a separate folder. The folder name corresponds to the template's unique
id.

`index.json` is a index file that contains meta information on all templates which is read by the `dso init`/`dso create`
commands. The `index.json` file needs to adhere to [this JSON schema](https://github.com/Boehringer-Ingelheim/dso/blob/main/src/dso/templates/schema.json). For a full example, check out DSO's [default library on GitHub](https://github.com/Boehringer-Ingelheim/dso/tree/main/src/dso/templates).

```json
{
    "id": "mylibrary",
    "description": "My amazing library",
    "init": [
        {
            "id": "my_project_template",
            "description": "...",
            "usage": "After initializing this project template, please configure the settings in ...",
            "params": [
                {
                    "name": "name",
                    "description": "Folder name used for the project"
                },
                // ... Add arbitrary custom parameters here. The CLI will prompt for them when initalizing the template
            ]
        }
    ],
    "folder": [], // follows the same structure as "init"
    "stage": [], // follows the same structure as "init"
}
```

## Writing templates

Template directories are recursively copied to their destination and files are rendered with [jinja2](https://jinja.palletsprojects.com/en/stable/templates/).
You can use all features of jinja2 such as `if/else` blocks or loops. You have access to all variables that
are defined in the `index.json` as described above.

Additionally, for `folder` and `stage` templates, the variable `rel_path_from_project_root` gets injected. As
the name suggests, it provides the path to the stage/folder relative to the project root.
