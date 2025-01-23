# Usage

## Installation

The DSO Python API is part of the DSO CLI package. See [installation](cli_installation.md) for more details.

## Typical usage

The purpose of the Python API is to provide convenient access to stage parameters from Python scripts or notebooks.
Using {func}`~dso.read_params` the `params.yaml` file of the specified stage is compiled and loaded
into a dictionary. The path must be specified relative to the project root -- this ensures that the correct stage is
found irrespective of the current working directory, as long as it the project root or any subdirectory thereof.
Only parameters that are declared as `params`, `dep`, or `output` in dvc.yaml are loaded to
ensure that one does not forget to keep the `dvc.yaml` updated.

```python
from dso import read_params

params = read_params("subfolder/my_stage")
```

By default, DSO compiles paths in configuration files to paths relative to each stage (see [configuration](cli_configuration.md#project-specific-settings----pyprojecttoml)).
From Python, you can use {func}`~dso.stage_here` to resolve paths
relative to the current stage independent of your current working directory, e.g.

```python
import pandas as pd
from dso import stage_here

pd.read_csv(stage_here(params["samplesheet"]))
```

This works, because `read_params` has stored the path of the current stage in a configuration object that persists in
the current Python session. `stage_here` can use this information to resolve relative paths.
