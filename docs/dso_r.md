# DSO R package

The DSO R-package provides access to files and configurations of a DSO project.

## Installation

The DSO R-Package is published on github. See [dso-r](https://github.com/Boehringer-Ingelheim/dso-r) for more details.

## Typical usage

The purpose of the DSO R-Package is to provide convenient access to stage parameters from R scripts or notebooks.
Using {func}`~read_params` the `params.yaml` file of the specified stage is compiled and loaded
into a dictionary. The path must be specified relative to the project root -- this ensures that the correct stage is
found irrespective of the current working directory, as long as it the project root or any subdirectory thereof.
Only parameters that are declared as `params`, `dep`, or `output` in dvc.yaml are loaded to
ensure that one does not forget to keep the `dvc.yaml` updated.

```r
library(dso)

params <- read_params("subfolder/my_stage")

# Access parameters
params$thresholds
params$samplesheet
```

By default, DSO compiles paths in configuration files to paths relative to each stage (see [configuration](cli_configuration.md#pyprojecttoml)).
From R, you can use {func}`~stage_here` to resolve paths
relative to the current stage independent of your current working directory.
This works, because `read_params` has stored the path of the current stage in a configuration object that persists in
the current R session. `stage_here` can use this information to resolve relative paths.

```r
samplesheet <- readr::read_csv(stage_here(params$samplesheet))
```

When modifying the `dvc.yaml`, `params.in.yaml`, or `params.yaml` files during development, use the {func}`~reload(params)`
function to ensure proper application of the changes by rebuilding and reloading the configuration.

```r
reload(params)
```

Creating a stage within the R environment can be performed using {func}`~create_stage`
and supplying it with the relative path of the stage from project root and a description.

```r
create_stage(name = "subfolder/my_stage", description = "This stage does something")
```
