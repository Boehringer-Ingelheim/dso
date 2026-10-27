from os import chdir
from pathlib import Path
from textwrap import dedent

import pytest
from click.testing import CliRunner

from dso._lint import DSO001, DSOLinter, LintError, QuartoRule, Rule
from dso.cli import dso_lint


@pytest.mark.parametrize(
    "file,expected",
    [
        ("dvc.yaml", True),
        ("some/path/to/dvc.yaml", True),
        ("/some/path/to/dvc.yaml", True),
        ("dvc.yaml.old", False),
        ("dvc.lock", True),
        ("other.dvc.lock", False),
        ("some/file.dvc", True),
        ("some/file.dvc/other.txt", False),
    ],
)
def test_rule_is_applicable(file, expected):
    file = Path(file)

    class MockRule(Rule):
        PATTERN = r"dvc\.yaml|dvc\.lock|.*\.dvc"

    assert MockRule.is_applicable(file) == expected


@pytest.mark.parametrize(
    "file,expected",
    [
        ("README.md", False),
        (".dvc/config", False),
        ("quarto_stage/README.md", True),
        ("quarto_stage/src/quarto_stage.qmd", True),
        ("quarto_stage/some/very_long/path/with/many/subfloders/hello.txt", True),
    ],
)
def test_quarto_rule_is_applicable(quarto_stage, file, expected):
    proj_root = quarto_stage / ".."
    file = proj_root / file

    class MockQuartoRule(QuartoRule):
        pass

    assert MockQuartoRule.is_applicable(file) == expected


@pytest.mark.parametrize(
    "file,expected",
    [
        ("README.md", False),
        (".dvc/config", False),
        ("quarto_stage/README.md", False),
        ("quarto_stage/src/quarto_stage.qmd", True),
        ("quarto_stage/some/very_long/path/with/many/subfloders/hello.txt", False),
    ],
)
def test_quarto_rule_is_applicable_pattern(quarto_stage, file, expected):
    proj_root = quarto_stage / ".."
    file = proj_root / file

    class MockQuartoRule(QuartoRule):
        PATTERN = r".*\.qmd"

    assert MockQuartoRule.is_applicable(file) == expected


@pytest.mark.parametrize(
    "r_snippet,expected",
    [
        (
            """params = read_params("quarto_stage")""",
            None,
        ),
        (
            """params = read_params("quarto_stage", quiet=TRUE)""",
            None,
        ),
        (
            """params = read_params("quarto_stage"\n, quiet=TRUE)""",
            None,
        ),
        (
            """foo = read_params("quarto_stage")""",
            None,
        ),
        (
            """read_params("quarto_stage")""",
            None,
        ),
        (
            """\
            params=read_params(
                "quarto_stage"
            )
            """,
            None,
        ),
        (
            """params <- read_params ("quarto_stage")""",
            None,
        ),
        (
            """params = read_params("quarto_stage/")""",
            None,
        ),
        (
            """\
            params = read_params("quarto_stage")
            params = read_params("quarto_stage")
            """,
            LintError,
        ),
        (
            """\
            params = read_params("quarto_stage")
            # params = read_params("quarto_stage")
            """,
            None,
        ),
        # TODO no good way to cover that with regex alone, see https://github.com/Boehringer-Ingelheim/dso/issues/66
        # (
        #     """\
        #     params = read_params("quarto_stage")
        #     print(" foo # no comment"); params = read_params("quarto_stage")
        #     """,
        #     LintError,
        # ),
        (
            """\
            params = read_params("wrong_path")
            """,
            LintError,
        ),
        ("", LintError),
        (
            """\
            params = read_params("quarto_stage")
            """,
            None,
        ),
    ],
)
def test_dso001(quarto_stage, r_snippet, expected: type[Exception] | None):
    file = quarto_stage / "src" / "quarto_stage.qmd"
    template = dedent(
        """\
        ---
        title: test
        ---

        ```{{r}}
        {snippet}
        ```
        """
    )
    file.write_text(template.format(snippet=dedent(r_snippet)))
    if expected is not None:
        with pytest.raises(expected):
            DSO001.check(file)
    else:
        DSO001.check(file)


@pytest.mark.parametrize("skip,expect_warn,expect_error", [(False, 0, 1), (True, 0, 0)])
def test_lint(quarto_stage, skip, expect_warn, expect_error):
    class MockRule(Rule):
        @classmethod
        def check(cls, file):
            raise LintError()

    linter = DSOLinter([MockRule])

    if skip:
        # Mofiy params.yaml to skip linting
        (quarto_stage / "params.yaml").write_text(
            dedent(
                """\
                dso:
                    lint:
                        exclude: [MockRule]
                """
            )
        )

    warn, error = linter.lint(quarto_stage / "src" / "quarto_stage.qmd")
    assert warn == expect_warn
    assert error == expect_error


@pytest.mark.parametrize(
    "paths",
    [
        ["."],
        [".pre-commit-config.yaml", "dvc.yaml"],
    ],
)
def test_lint_cli(dso_project, paths):
    runner = CliRunner()
    chdir(dso_project)  # proj root
    result = runner.invoke(dso_lint, paths)
    print(result.output)
    assert result.exit_code == 0
