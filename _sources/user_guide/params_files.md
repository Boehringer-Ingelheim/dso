# Params files

This section is the reference guide for configuration files. Explain inheritance, jinja 2 etc. in detail.

TODO

## Compiling `params.yaml` files

All `params.yaml` files are automatically generated using:

```bash
dso compile-config
```

## Overwriting Parameters

When multiple `params.in.yaml` files (such as those at the project, folder, or stage level) contain the same configuration, the value specified at the more specific level (e.g., stage) takes precedence over the value set at the broader level (e.g., project). This makes the analysis adaptable and enhances modifiability across the project.
