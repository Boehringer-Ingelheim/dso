# Getting started

# Getting Started with DSO

Welcome to the DSO (Data Science Operations) project! This guide will help you set up your project, configure your environment, and start using DSO and DVC for data version control and reproducible analyses.

## Introduction

DevOps practices empower data science teams to streamline their workflows, minimizing the time from change to finished analysis reports. By integrating development and operations, they can automate processes and ensure reproducibility and robustness.

The DSO tool offers a flexible structure for data science projects with config management and supports the use of Git for code versioning and Data Version Control (DVC) for data versioning, compiling, and configurations. The two core units of a DSO project are folders and stages, where a stage is an executable step for an analysis.

## Installation

You can install the latest version with pip using
```bash
pip install dso-core
```

Alternatively, you can install the development version from GitHub:
```bash
pip install git+https://github.com/Boehringer-Ingelheim/dso.git@main
```

## Initialise a project
In the context of DSO, a project is a structured environment where data science workflows are organized and managed. It serves as the root directory that contains all the necessary components for conducting data analyses.

To initialize a project use the following command:

```bash
dso init
# Please enter the name of the project, e.g. "single_cell_lung_atlas":
# Please add a short description of the project:
```

By initializing the project, the project folder will be created with all the essential components for using `git`, `dvc`, and `dso`.

## Create folders and stages

### Folders

A folder in DSO is a directory that helps organize different parts of your project. Folders can be nested to create a hierarchical structure that reflects the organization of your project, studies, workpackages, and stages.

To set-up a folder, use:
```bash
dso create folder
# Please enter the name of the folder, e.g. "RNAseq":
```

### Stages

A stage in DSO represents an executable step in your data analysis pipeline. Each stage is represented with directory containing several sub-directories. A stage usually performs some type of analysis within your analysis pipeline, such as preprocessing of sequencing data or differential expression analysis.

Each project or folder can have several stages and therefore it is recommended to adhere to a hierarchical structure numbering stages according to their position in your analysis pipeline.

To create a stage use:
```bash
dso create stage
# ? Choose a template: (Use arrow keys)
#   bash
#   quarto

# Please enter the name of the stage, e.g. "01_preprocessing": 01_preprocessing
# Please add a short description of the stage: Preprocessing stage
```

For now, two stage types are implemented. One is for


###
Setting Up Your Project
Create Folders and Stages
Create a Folder Use dso create folder to create a new folder for your project:

```bash
dso create folder
# Please enter the name of the folder, e.g. "RNAseq"
```

Create a Stage Use dso create stage to create a new stage within your folder:

```bash
dso create stage
# Please enter the name of the stage, e.g. "01_preprocessing":
```

Configure Remote Storage
Add Remote Storage Add a remote storage to store version-controlled data:
dvc remote add -d myremote /path/to/project/_DVC_STORAGE

Configure Git to Track DVC Files Configure Git to automatically track .dvc files:
dvc config core.autostage true
git commit .dvc/config -m "Configure remote storage"

## Writing Config Files
params.in.yaml
Edit the params.in.yaml file to specify your parameters:

thresholds:
  fc: 2
  p_value: 0.05
  p_adjusted: 0.1

samplesheet: !path "01_preprocessing/input/samplesheet.txt"
metadata_file: !path "metadata/metadata.csv"
sdtm_data_path: "/path/to/data/"
remove_outliers: true
exclude_samples:
  - Sample_1
  - Sample_2

Compile Config Files
Compile the config files to generate params.yaml:

dso compile-config

## Using DVC
Track Changes with DVC
Add Files to DVC Track changes of input or output files/directories:
dvc add <filename/directoryname>

Push Changes to Remote Storage Push your local data changes to the remote storage:
dvc push

Pull Changes from Remote Storage Pull the latest data from the remote storage:
dvc pull

## Running Your Analysis
Create and Run Stages
Create a Stage Create a new stage for your analysis:
dso create stage 01_analysis

Define Stage in dvc.yaml Edit the dvc.yaml file to define your stage:
stages:
  01_analysis:
    params:
      - dso
      - thresholds
    deps:
      - src/01_analysis.qmd
      - ${samplesheet}
    outs:
      - output
      - report/01_analysis.html
    cmd:
      - dso exec quarto .

Run the Stage Run your analysis stage:
dso repro

## Conclusion
Congratulations! You have successfully set up your DSO project and run your first analysis. For more detailed information, refer to the DSO Documentation.
TODO
