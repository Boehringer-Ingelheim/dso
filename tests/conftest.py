from os import chdir
from pathlib import Path
from textwrap import dedent

from click.testing import CliRunner
from dso._compile_config import compile_all_configs
from dso._logging import log
from dso.cli import dso_create, dso_init
from pytest import fixture

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
    runner.invoke(
        dso_create,
        [
            "stage",
            stage_name,
            "--template",
            "quarto_r",
            "--description",
            "a quarto stage",
        ],
    )
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
    lines = [
        line
        for line in (quarto_stage / "dvc.yaml").read_text().splitlines()
        if "dso.quarto" not in line
    ]
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


@fixture
def dso_project_with_multiple_stages(tmp_path) -> Path:
    """
    Create a DSO project with different stages and folder
    Returns the path to the project root.
    """

    log.debug("[yellow]Creating fixture with multiple folders and stages")
    runner = CliRunner()
    proj_name = "dso_project_multi"
    chdir(tmp_path)

    runner.invoke(
        dso_init, [proj_name, "--description", "a test project with multiple stages"]
    )
    project_path = tmp_path / proj_name
    chdir(project_path)

    path_0100 = project_path / "0100_ETL"
    path_0200 = project_path / "0200_AnalysisA"
    path_0300 = project_path / "0300_AnalysisB"

    log.debug("Create all the main folders")
    result = runner.invoke(dso_create, ["folder", str(path_0100)])
    assert result.exit_code == 0
    result = runner.invoke(dso_create, ["folder", str(path_0200)])
    assert result.exit_code == 0
    result = runner.invoke(dso_create, ["folder", str(path_0300)])
    assert result.exit_code == 0

    log.debug("Create stages for 0100")
    runner.invoke(
        dso_create,
        [
            "stage",
            str(path_0100 / "0101_ETL"),
            "--template",
            "quarto_r",
            "--description",
            "ETL",
        ],
    )
    runner.invoke(
        dso_create,
        [
            "stage",
            str(path_0100 / "0102_ETLA"),
            "--template",
            "quarto_r",
            "--description",
            "ETL",
        ],
    )

    log.debug("Create same stages for 0200 and 0300 for testing reasons")

    stage_names = ["01_Preprocessing", "02_Analysis", "03_Exploring", "04_Reporting"]
    for stage in stage_names:
        runner.invoke(
            dso_create,
            [
                "stage",
                str(path_0200 / stage),
                "--template",
                "quarto_r",
                "--description",
                f"{stage} stage",
            ],
        )

        runner.invoke(
            dso_create,
            [
                "stage",
                str(path_0300 / stage),
                "--template",
                "quarto_r",
                "--description",
                f"{stage} stage",
            ],
        )

    log.debug("Create input test files in each stage")
    for file_name in [
        path_0100 / "0101_ETL" / "input" / "A.txt",
        path_0100 / "0102_ETLA" / "input" / "B.txt",
        path_0200 / "01_Preprocessing" / "input" / "C.txt",
        path_0200 / "02_Analysis" / "input" / "D.txt",
        path_0200 / "03_Exploring" / "input" / "E.txt",
        path_0200 / "04_Reporting" / "input" / "F.txt",
        path_0300 / "01_Preprocessing" / "input" / "G.txt",
        path_0300 / "02_Analysis" / "input" / "H.txt",
        path_0300 / "03_Exploring" / "input" / "I.txt",
        path_0300 / "04_Reporting" / "input" / "J.txt",
    ]:
        (file_name).touch()

    log.debug("Add file paths in params.in.yaml files")
    with (project_path / "params.in.yaml").open("w") as f:
        f.write(
            dedent(
                """\
                from_root:
                    A: !path 0100_ETL/0101_ETL/input/A.txt
                    B: !path 0100_ETL/0102_ETLA/input/B.txt
                    C: !path 0200_AnalysisA/01_Preprocessing/input/C.txt
                    D: !path 0200_AnalysisA/02_Analysis/input/D.txt
                    E: !path 0200_AnalysisA/03_Exploring/input/E.txt
                    F: !path 0200_AnalysisA/04_Reporting/input/F.txt
                    G: !path 0300_AnalysisB/01_Preprocessing/input/G.txt
                    H: !path 0300_AnalysisB/02_Analysis/input/H.txt
                    I: !path 0300_AnalysisB/03_Exploring/input/I.txt
                    J: !path 0300_AnalysisB/04_Reporting/input/J.txt
                """
            )
        )

    with (path_0200 / "params.in.yaml").open("w") as f:
        f.write(
            dedent(
                """\
                from_0200:
                    A: !path ../0100_ETL/0101_ETL/input/A.txt
                    B: !path ../0100_ETL/0102_ETLA/input/B.txt
                    C: !path 01_Preprocessing/input/C.txt
                    D: !path 02_Analysis/input/D.txt
                    E: !path 03_Exploring/input/E.txt
                    F: !path 04_Reporting/input/F.txt
                    G: !path ../0300_AnalysisB/01_Preprocessing/input/G.txt
                    H: !path ../0300_AnalysisB/02_Analysis/input/H.txt
                    I: !path ../0300_AnalysisB/03_Exploring/input/I.txt
                    J: !path ../0300_AnalysisB/04_Reporting/input/J.txt
                """
            )
        )

    with (path_0300 / "params.in.yaml").open("w") as f:
        f.write(
            dedent(
                """\
                from_0300:
                    A: !path ../0100_ETL/0101_ETL/input/A.txt
                    B: !path ../0100_ETL/0102_ETLA/input/B.txt
                    C: !path ../0200_AnalysisA/01_Preprocessing/input/C.txt
                    D: !path ../0200_AnalysisA/02_Analysis/input/D.txt
                    E: !path ../0200_AnalysisA/03_Exploring/input/E.txt
                    F: !path ../0200_AnalysisA/04_Reporting/input/F.txt
                    G: !path 01_Preprocessing/input/G.txt
                    H: !path 02_Analysis/input/H.txt
                    I: !path 03_Exploring/input/I.txt
                    J: !path 04_Reporting/input/J.txt
                """
            )
        )

    with (path_0100 / "params.in.yaml").open("w") as f:
        f.write(
            dedent(
                """\
                from_0100:
                    A: !path 0101_ETL/input/A.txt
                    B: !path 0102_ETLA/input/B.txt
                    C: !path ../0200_AnalysisA/01_Preprocessing/input/C.txt
                    D: !path ../0200_AnalysisA/02_Analysis/input/D.txt
                    E: !path ../0200_AnalysisA/03_Exploring/input/E.txt
                    F: !path ../0200_AnalysisA/04_Reporting/input/F.txt
                    G: !path ../0300_AnalysisB/01_Preprocessing/input/G.txt
                    H: !path ../0300_AnalysisB/02_Analysis/input/H.txt
                    I: !path ../0300_AnalysisB/03_Exploring/input/I.txt
                    J: !path ../0300_AnalysisB/04_Reporting/input/J.txt
                """
            )
        )

    with (path_0200 / "0200_AnalysisA" / "01_Preprocessing" / "params.in.yaml").open(
        "w"
    ) as f:
        f.write(
            dedent(
                """\
                from_0201:
                    A: !path ../../0100_ETL/0101_ETL/input/A.txt
                    B: !path ../../0100_ETL/0102_ETLA/input/B.txt
                    C: !path input/C.txt
                    D: !path ../02_Analysis/input/D.txt
                    E: !path ../03_Exploring/input/E.txt
                    F: !path ../04_Reporting/input/F.txt
                    G: !path ../../0300_AnalysisB/01_Preprocessing/input/G.txt
                    H: !path ../../0300_AnalysisB/02_Analysis/input/H.txt
                    I: !path ../../0300_AnalysisB/03_Exploring/input/I.txt
                    J: !path ../../0300_AnalysisB/04_Reporting/input/J.txt
                """
            )
        )

    return project_path
