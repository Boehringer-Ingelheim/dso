# Collaborating on an existing DSO/DVC Project

If a DSO project is already set up and you want to collaborate or extend it, follow these guidelines. For general information about DSO or DVC, please check out the [DSO getting-started page](../tutorials/getting_started.md) and the [DVC documentation](https://dvc.org/doc).

## Requirements

-   The original project was initialized with `dso init` and contains all essential files.
-   A DVC remote storage is set up where all DVC-controlled data is stored.
-   A Git repository exists and can be cloned.

## How-To

### Clone the Git Repository

First, clone the existing git repository of the project.

```bash
git clone <git_repository>
```

### Pull the Data from the Remote Repository

After cloning, no DVC-controlled input or output data is locally available. Therefore, it is required to pull the data associated with the repository from the DVC remote storage. Use:

```bash
# Compiles all params.in.yaml into params.yaml files and pulls the DVC-controlled data
dso pull
```

### Make changes to DSO Project

After pulling the source code from the git repository and the respective data from the DVC remote storage, everything is set-up to make changes and expand on the dso project. Please follow the instructions on how-to set-up folders, stages, or configuration files described in the [dso getting-started page](../tutorials/getting_started.md).
