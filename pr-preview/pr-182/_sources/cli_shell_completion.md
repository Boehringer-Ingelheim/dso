# Shell completion

`dso` supports shell-completion through [click](https://click.palletsprojects.com/en/stable/shell-completion/#enabling-completion).

To enable shell-completion, add the corresponding line to your `.bashrc`/`.zshrc`:

```bash
# bash
eval "$(_DSO_COMPLETE=bash_source dso)"

# zsh
eval "$(_DSO_COMPLETE=zsh_source dso)"
```
