"""Linting functions for DSO projects"""

import re
import sys
from abc import ABC, abstractmethod
from collections.abc import Collection, Sequence
from functools import cache
from os import chdir
from pathlib import Path

from ruamel.yaml import YAML

from dso._logging import log
from dso._util import check_project_roots, find_in_parent, get_project_root, git_list_files


class LintError(Exception):
    """Custom Exception class for a failed linting test"""

    pass


class LintWarning(UserWarning):
    """Custom Exception class for a lint warning"""

    pass


class Rule(ABC):
    """Abstract base class for a linting rule"""

    PATTERN = r".*"

    @staticmethod
    def _match_filename_pattern(pattern: str, file: Path):
        return re.fullmatch(pattern, file.name) is not None

    @classmethod
    def is_applicable(cls: type["Rule"], file: Path) -> bool:
        """
        Check if the rule is applicable to `file`.

        The check is based on a file pattern and potentially other criteria defined by the Rule.
        """
        return Rule._match_filename_pattern(cls.PATTERN, file)

    @classmethod
    @abstractmethod
    def check(cls: type["Rule"], file: Path) -> None:
        """
        Check if the file passes the linting check.

        Doesn't return anything but raises either a LintError or LintWarning
        """
        ...


class QuartoRule(Rule):
    """Common base class for rules that apply to quarto stages."""

    @classmethod
    def is_applicable(cls: type["QuartoRule"], file: Path) -> bool:
        """
        Check if the rule is applicable to `file`.

        Return true, if "dso exec quarto" is found in the dvc.yaml associated with this stage AND
        the file matches the pattern
        """
        dvc_yaml = find_in_parent(file, "dvc.yaml", get_project_root(file))
        assert dvc_yaml is not None, "No dvc.yaml found in project"
        is_quarto_stage = "dso exec quarto ." in dvc_yaml.read_text()
        return is_quarto_stage and Rule._match_filename_pattern(cls.PATTERN, file)


class DSO001(QuartoRule):
    """In a quarto stage, ensure `dso::read_params` is called and stage name is correct"""

    PATTERN = r".*\.qmd"  # and dvc.yaml contains "dso exec quarto"

    @classmethod
    def check(cls, file):
        """Check that the file passes the linting step."""
        root_path = get_project_root(file)
        stage_path_expected = find_in_parent(file, "dvc.yaml", root_path)
        assert stage_path_expected is not None, "No dvc.yaml found in project"
        # .parent to remove the dvc.yaml filename
        stage_path_expected = str(stage_path_expected.parent.relative_to(root_path))
        content = file.read_text()

        # remove comments
        # TODO there are still edge cases, e.g. a `#` within a string doesn't initiate a comment
        # However this is hard/impossible (?) to solve with a regular expression alone, we'd need a proper
        # R parse to address all edge cases. See also https://github.com/Boehringer-Ingelheim/dso/issues/66
        pattern_is_comment = re.compile(r"#.*$")
        content = "\n".join([re.sub(pattern_is_comment, "", line) for line in content.split("\n")])

        # detect pattern
        pattern = r"[\s\S]*?(dso::)?read_params\s*\(([\s\S]*?)(\s*,.*)?\)"
        res = re.findall(pattern, content, flags=re.MULTILINE)
        if len(res) == 0:
            raise LintError(f"no `params = read_params('{stage_path_expected}')` statement found in qmd document")
        if len(res) > 1:
            raise LintError("Multiple read_params statements found")
        stage_path = res[0][1].strip().strip("'\"").rstrip("/")  # get what's within the brackets for read_params
        if stage_path_expected != stage_path:
            raise LintError(
                f"Stage path specified in read_params doesn't match. Expected: {stage_path_expected}, Actual: {stage_path}"
            )


class DSO002(QuartoRule):
    """Quarto stage has dso.quarto as params dependency"""

    PATTERN = r"dvc\.yaml"  # and cmd contains "dso exec quarto"

    @classmethod
    def check(cls, file):
        """Check that the file passes the linting step."""
        raise NotImplementedError


class DSO003(QuartoRule):
    """Quarto stage declares an HTML output"""

    PATTERN = r"dvc\.yaml"  # and cmd contains "dso exec quarto"

    @classmethod
    def check(cls, file):
        """Check that the file passes the linting step."""
        raise NotImplementedError


class DSO004(QuartoRule):
    """quarto stage declares src/*.qmd as input"""

    PATTERN = r"dvc\.yaml"  # and cmd contains "dso exec quarto"

    @classmethod
    def check(cls, file):
        """Check that the file passes the linting step."""
        raise NotImplementedError


class DSO005(Rule):
    """all parameters accessed from `cmd` section are declared as deps or params"""

    PATTERN = r"dvc\.yaml"  # general rule, applies to all stage types


class DSO006(Rule):
    """Inputs declared in at least one dvc.yaml file are either generated by dvc or have a `.dvc` file or are outside the repo"""

    PATTERN = r"dvc\.yaml|dvc\.lock|.*\.dvc"

    @classmethod
    def check(cls, file):
        """Check that the file passes the linting step."""
        raise NotImplementedError


class DSO007(Rule):
    """
    Relative paths are declared with !path.

    (failure if it looks like a relative path and exists, warning otherwise because it could be something else)
    """

    PATTERN = r"params\.in\.yaml"

    @classmethod
    def check(cls, file):
        """Check that the file passes the linting step."""
        raise NotImplementedError


class DSOLinter:
    """Lint according to some rules"""

    ALL_RULES = [
        DSO001,
        # DSO002, DSO003, DSO004, DSO005, DSO006, DSO007, DSO008
    ]

    def __init__(self, rules: Collection[type[Rule]] = ALL_RULES):
        self.rules = rules

    @cache
    @staticmethod
    def _get_linting_config(config_file: Path):
        """Get the linting config from a params.yaml file"""
        yaml = YAML(typ="safe")
        config = yaml.load(config_file)
        dso_config = config.get("dso", {})
        if dso_config is None:
            dso_config = {}
        lint_config = dso_config.get("lint", {})
        if lint_config is None:
            lint_config = {}
        return lint_config

    def lint(self, file: Path):
        """Apply all linting rules to a file"""
        if not file.is_file():
            raise ValueError("Only existing files (not directories) may be passed to linter")

        config_path = find_in_parent(file, "params.yaml", get_project_root(file))
        assert config_path is not None, "No params.yaml found in project"
        config = DSOLinter._get_linting_config(config_path)
        rules = [r for r in self.rules if r.__name__ not in config.get("exclude", [])]

        warn = error = 0
        for r in rules:
            if r.is_applicable(file):
                try:
                    log.debug(f"Linting ./{file}")
                    r.check(file)
                except LintWarning as w:
                    log.warning(f"{w} (./{file})")
                    warn += 1
                except LintError as e:
                    log.error(f"{e} (./{file})")
                    error += 1

        return warn, error


def lint(paths: Sequence[Path]):
    """
    Lint all files in paths

    If paths contains a directory, it will be expanded to all files contained within.
    """
    proj_root = check_project_roots(paths).absolute()

    linter = DSOLinter()
    files = set()
    for p in paths:
        p = p.absolute()
        if p.is_file():
            files.add(p)
        else:
            files.update(git_list_files(p))

    log.info(f"Compiled a list of {len(files)} to be linted")

    chdir(proj_root)
    warn = error = 0
    for f in files:
        # use relative path for more readable error messages
        tmp_warn, tmp_error = linter.lint(f.relative_to(proj_root))
        warn += tmp_warn
        error += tmp_error

    if error:
        log.error(f"Linting completed with {warn} warnings and {error} errors")
    elif warn:
        log.warning(f"Linting completed with {warn} warnings and {error} errors")
    if error:
        sys.exit(1)
