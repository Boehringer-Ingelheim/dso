# Configuration

This section provides and overview of dso settings and how to apply them.

## pyproject.toml

Project-specific dso settings can be set in the `pyproject.toml` file at the root of each project in the
`[tool.dso]` section:

```toml
[tool.dso]
# whether to compile relative paths declared with `!path` into absolute paths or relative paths (relative to each stage).
# default is `true`
use_relative_path = true
```
