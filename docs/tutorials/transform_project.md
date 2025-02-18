# Transforming an existing project into DSO format

Transforming a project into the DSO format is best done in a separate Git branch to ensure the integrity of the original analysis. Additionally, the transformation can be done step-by-step, transforming single analysis stages at a time.

## Initializing DSO in your project and folders

The easiest way to obtain all essential DSO files for your project is to use the DSO command `dso init` on project root level. Without specifying any additional path, `dso init` will ask whether you want to initialize the DSO folder structure in the current directory.
When applied to an existing directory, `dso init` will add missing files, but never change or replace any existing file.

Usage:

```bash
dso init
# Please enter the name of the project, e.g., "single_cell_lung_atlas":
# Directory already exists. Do you want to initialize DSO in an existing project? [y/n]: y
```

This also applies to folders that organize your project. To transform folders to be usable in the DSO/DVC environment use:

```bash
dso create folder
# Please enter the name of the folder, e.g., "RNAseq":
# Directory already exists. Do you want to copy template files to existing folder? [y/n]: y
```

## Set-up the DVC remote storage

DVC needs a remote storage where your DVC-controlled input and output files are stored.

```bash
# Create a directory for storing version-controlled files
mkdir /path/on/shared/filesystem/project1/DVC_STORAGE

# Execute within the project directory to define the remote storage
dvc remote add -d <remote_name> /path/on/shared/filesystem/project1/DVC_STORAGE
```

## Transforming analysis scripts to stages

The last step is to transform the written analysis scripts into stages. To create a stage, use:

```bash
dso create stage <stage_name> # e.g. 01_preprocessing
```

How-to set-up a stage and the configuration files can be found on the [dso getting-started page](../tutorials/getting_started.md).
The following list describes the most important tasks in transforming your analysis scripts to stages.

-   Define all parameters and stage input files/folders in a params.in.yaml.
-   Avoid duplicate entries and use parameter inheritance to your advantage.
-   If multiple stages use an input file or a parameter, define it in the `params.in.yaml` of a higher level folder.
-   Define all parameters and dependencies in the dvc.yaml that are used within the stage.
-   Use absolute paths when data is not DVC-controlled and stored within your repository.
-   Use relative paths for stage outputs and DVC-controlled inputs.
-   Use `!path` in your `params.in.yaml` when using relative paths to files/folders - `!path` resolves the relative path regardless of the current folder or stage.
-   To track files/folders using DVC, use `dvc add <filename/foldername>`.
-   Use the `read_params()` function implemented in the DSO R-package and the DSO Python API to read configuration files in your analysis scripts.
-   Use `stage_here()` to resolve relative paths from your `params.yaml`.
-   Write all output files generated within a stage into the output directory.
