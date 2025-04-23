from os import chdir
from shutil import copyfile
from textwrap import dedent

from click.testing import CliRunner

from dso._quarto import render_quarto
from dso.cli import dso_exec
from tests.conftest import TESTDATA


def test_pandocfilter(quarto_stage):
    copyfile(TESTDATA / "git_logo.png", quarto_stage / "src" / "git_logo.png")
    copyfile(TESTDATA / "git_logo.pdf", quarto_stage / "src" / "git_logo.pdf")
    copyfile(TESTDATA / "git_logo.svg", quarto_stage / "src" / "git_logo.svg")
    copyfile(TESTDATA / "git_logo.svg", quarto_stage / "src" / "git logo.svg")
    (quarto_stage / "src" / "_quarto.yml").write_text(
        dedent(
            """\
            format:
                html:
                    fig-format: svg
                    toc: true
                    code-fold: true
                    embed-resources: true
            disclaimer:
                title: Disclaimer
                text: This is a disclaimer
            watermark:
                text: WATERMARK
                tile_size: [100, 100]
                font_size: 12
                font_outline: 2
                font_color: black
                font_outline_color: "#AA111160"
            """
        )
    )
    (quarto_stage / "src" / "quarto_stage.qmd").write_text(
        dedent(
            """\
            This is a quarto document with

            a PNG Image

            ![PNG Image](git_logo.png)

            a PDF Image

            ![PDF Image](git_logo.pdf)

            and an SVG image

            ![SVG Image](git_logo.svg)

            and an SVG image with a space in the filename

            ![SVG Imag2](git%20logo.svg)
            """
        )
    )

    render_quarto(
        quarto_stage / "src",
        quarto_stage / "report",
        before_script="",
        cwd=quarto_stage,
        with_pandocfilter=True,
    )
    out_html = (quarto_stage / "report" / "quarto_stage.html").read_text()
    assert "Disclaimer" in out_html
    assert "This is a disclaimer" in out_html
    assert "callout-important" in out_html


def test_override_config(quarto_stage):
    """Test that it's possible to remove a watermark/disclaimer by overriding the config with null"""
    # I didn't find a straightforward way of testing programmatically that there's really no watermark.
    # this test still guarantees that it doesn't fail with an error when overring the watermark config (which it did previously)
    (quarto_stage / ".." / "params.in.yaml").write_text(
        dedent(
            """\
            dso:
              quarto:
                watermark:
                  text: test
                disclaimer:
                  title: test disclaimer
                  text: lorem ipsum
            """
        )
    )
    (quarto_stage / "params.in.yaml").write_text(
        dedent(
            """\
            dso:
              quarto:
                watermark: null
                disclaimer: null
            """
        )
    )

    runner = CliRunner()
    chdir(quarto_stage)
    stage_path = "."

    result = runner.invoke(dso_exec, ["quarto", stage_path])
    assert result.exit_code == 0

    out_html = (quarto_stage / "report" / "quarto_stage.html").read_text()
    assert "test disclaimer" not in out_html
