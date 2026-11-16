# pre-commit integration

[Pre-commit](https://pre-commit.com/) hooks are small scripts that perform consistency checks on
files in the repository before actually performing a git commit (or push).
If the checks fail, the commit will be aborted and needs to be retried once the problems have been
fixed. Some issues can automatically be fixed by the hooks.

Pre-commit hooks are defined in a `.pre-commit-config.yaml` file at the root
of a repository. The [DSO project template](templates.md) comes with a default configuration that is detailled below.

To activate pre-commit integration, the hooks need to be installed in each repository separately. The DSO CLI
will ask the user whether to do so. You can also install the hooks manually by running

```bash
pre-commit install
```

This will write the hooks into the `.git` directory.

## Example

Let's assume we made some changes that are already in the git staging area (`git add`) and are about
to be committed.

```console
$> git commit
detect private key.......................................................Passed
check python ast.....................................(no files to check)Skipped
fix end of files.........................................................Failed
- hook id: end-of-file-fixer
- exit code: 1
- files were modified by this hook

Fixing params.in.yaml

mixed line ending........................................................Passed
trim trailing whitespace.................................................Passed
check for case conflicts.................................................Passed
check for merge conflicts................................................Passed
nbstripout...........................................(no files to check)Skipped
Run dso lint.............................................................Passed
```

The check failed, because the "end of file" has been fixed in one file. This now shows as "unstaged"
file in `git status`:

```console
$> git status
[...]
Changes not staged for commit:
  (use "git add <file>..." to update what will be committed)
  (use "git restore <file>..." to discard changes in working directory)
        modified:   params.in.yaml
```

We need to add those changes, and then redo the commit:

```console
$> git add params.in.yaml
$> git commit
detect private key.......................................................Passed
check python ast.....................................(no files to check)Skipped
fix end of files.........................................................Passed
mixed line ending........................................................Passed
trim trailing whitespace.................................................Passed
check for case conflicts.................................................Passed
check for merge conflicts................................................Passed
nbstripout...........................................(no files to check)Skipped
Run dso lint.............................................................Passed
[master d60efd3] update params
 1 file changed, 1 insertion(+)
```

Now all checks have passed and the commit has been created.

## pre-commit hooks

The following pre-commit hooks are included in the default configuration file:

-   [detect-private-key](https://github.com/pre-commit/pre-commit-hooks?tab=readme-ov-file#detect-private-key): Scans for private keys within files to prevent accidental exposure.
-   [check-ast](https://github.com/pre-commit/pre-commit-hooks?tab=readme-ov-file#check-ast): Parses Python files to catch syntax errors before commits.
-   [end-of-file-fixer](https://github.com/pre-commit/pre-commit-hooks?tab=readme-ov-file#end-of-file-fixer): Ensures every file ends with a newline.
-   [mixed-line-ending](https://github.com/pre-commit/pre-commit-hooks?tab=readme-ov-file#mixed-line-ending): Normalizes line endings to avoid mixing CRLF and LF.
-   [trailing-whitespace](https://github.com/pre-commit/pre-commit-hooks?tab=readme-ov-file#trailing-whitespace): Removes trailing whitespace from files.
-   [check-case-conflict](https://github.com/pre-commit/pre-commit-hooks?tab=readme-ov-file#check-case-conflict): Detects potential conflicts arising from case insensitive filenames.
-   [check-merge-conflict](https://github.com/pre-commit/pre-commit-hooks?tab=readme-ov-file#check-merge-conflict): Scans files for merge conflict markers.
-   [nbstripout](https://github.com/kynan/nbstripout): Remove outputs from jupyter notebooks (contents shall not go to git. Instead the rendered HTML file is tracked by dvc).
-   dso lint: Run the [dso linter](linting.md) on all files.

The following hooks are included, but commented out. These hooks are autoformatters for Python, R, Markdown and other files. We do recommend enabling them, but we acknowledge that not everyone may like them.

-   [Prettier](https://prettier.io/): formats Markdown, JSON, CSS, JS and others
-   [Ruff](https://astral.sh/ruff): Linter and formatter for Python (including jupyter notebooks)
-   [Styler](https://styler.r-lib.org/): Formatter for R and Rmarkdown notebooks.

## pre-push hooks

As the name suggests, `pre-push` hooks run before `git push`. The following hook is included in the default
configuration file:

-   dvc push: Run [dvc push](https://dvc.org/doc/command-reference/push#push) to ensure all data files are
    synced to the remote at the same time the code changes are pushed to the git remote.
