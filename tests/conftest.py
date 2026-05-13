from os import chdir
from pathlib import Path
from textwrap import dedent

from click.testing import CliRunner
from pytest import fixture

from dso._compile_config import compile_all_configs
from dso.cli import dso_create, dso_init

TESTDATA = Path(__file__).parent / "data"


@fixture
def dso_project(tmp_path) -> Path:
    """Create an empty DSO project in a temporary directory and return the path"""
    runner = CliRunner()
    proj_name = "dso_project"
    chdir(tmp_path)
    runner.invoke(dso_init, [proj_name, "--description", "a test project"])

    return tmp_path / proj_name


@fixture
def quarto_stage(dso_project) -> Path:
    """Create a DSO project with a quarto stage and return the path to that stage.

    The stage will use a Python quarto document, to make it easier to test it in a Python environment.
    """
    runner = CliRunner()
    stage_name = "quarto_stage"
    chdir(dso_project)
    runner.invoke(dso_create, ["stage", stage_name, "--template", "quarto_r", "--description", "a quarto stage"])
    with (Path(stage_name) / "src" / f"{stage_name}.qmd").open("w") as f:
        f.write(
            dedent(
                """\
                ```{python}
                print("Hello World!")
                from dso import read_params, stage_here
                read_params("quarto_stage")
                (stage_here("output") / "hello.txt").touch()
                ```
                """
            )
        )

    return dso_project / stage_name


@fixture
def quarto_stage_empty_configs(quarto_stage) -> Path:
    """
    DSO project with quarto stage, but with empty params.in.yaml files both in project root and stage
    """
    with (quarto_stage / ".." / "params.in.yaml").open("w") as f:
        f.write("\n")
    with (quarto_stage / "params.in.yaml").open("w") as f:
        f.write("\n")
    # remove param from `dvc.yaml` because it's not in the empty config anymore
    lines = [line for line in (quarto_stage / "dvc.yaml").read_text().splitlines() if "dso.quarto" not in line]
    (quarto_stage / "dvc.yaml").write_text("\n".join(lines) + "\n")
    compile_all_configs([quarto_stage])

    return quarto_stage


@fixture
def quarto_stage_bibliography(quarto_stage) -> Path:
    """
    DSO project with quarto stage, including a bibiliography file
    """
    bib_dir = quarto_stage / ".." / "bib"
    bib_dir.mkdir()
    with (bib_dir / "bibliography.bib").open("w") as f:
        f.write(
            dedent(
                """\
                @article{knuth1984literate,
                    title={Literate programming},
                    author={Knuth, Donald Ervin},
                    journal={The computer journal},
                    volume={27},
                    number={2},
                    pages={97--111},
                    year={1984},
                    publisher={Oxford University Press}
                }
                """
            )
        )
    with (quarto_stage / ".." / "params.in.yaml").open("w") as f:
        f.write(
            dedent(
                """\
                dso:
                  quarto:
                    bibliography: !path bib/bibliography.bib
                """
            )
        )
    with (quarto_stage / "src" / "quarto_stage.qmd").open("w+") as f:
        f.write("blah blah [@knuth1984literate]")

    return quarto_stage


@fixture
def quarto_stage_css(quarto_stage) -> Path:
    """
    DSO project with quarto stage, including a bibiliography file
    """
    style_dir = quarto_stage / ".." / "styles"
    style_dir.mkdir()
    with (style_dir / "s01.css").open("w") as f:
        f.write(
            dedent(
                """\
                h2.veryspecialclass1 {
                    font-size: huge
                }
                """
            )
        )
    with (style_dir / "s02.css").open("w") as f:
        f.write(
            dedent(
                """\
                h2.veryspecialclass2 {
                    font-size: huge
                }
                """
            )
        )
    with (quarto_stage / ".." / "params.in.yaml").open("w") as f:
        f.write(
            dedent(
                """\
                dso:
                  quarto:
                    css:
                       - !path styles/s01.css
                       - !path styles/s02.css
                    format:
                      html:
                        embed-resources: true
                """
            )
        )

    return quarto_stage
