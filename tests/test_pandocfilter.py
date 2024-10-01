from shutil import copyfile
from textwrap import dedent

from dso.exec import _render_quarto
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

    _render_quarto(
        quarto_stage / "src", quarto_stage / "report", before_script="", cwd=quarto_stage, with_pandocfilter=True
    )
    out_html = (quarto_stage / "report" / "quarto_stage.html").read_text()
    assert "Disclaimer" in out_html
    assert "This is a disclaimer" in out_html
    assert "callout-important" in out_html
