import hashlib
from os import chdir
from pathlib import Path
from shutil import copyfile
from textwrap import dedent

from click.testing import CliRunner
from panflute import Doc, MetaMap, MetaString, Para, RawBlock, Str
from ruamel.yaml import YAML

from dso._quarto import quarto_config_yml, render_quarto
from dso.cli import dso_exec
from dso.pandocfilter import action
from tests.conftest import TESTDATA


def _doc_with_watermark(text="WATERMARK"):
    """Build a minimal panflute Doc carrying a watermark config in its metadata."""
    return Doc(metadata=MetaMap(watermark=MetaMap(text=MetaString(text))))


def test_quarto_config_yml_registers_filters(tmp_path):
    """Disclaimer and watermark filters are registered at the right entry points, in addition to user filters."""
    config = {"disclaimer": {"title": "t", "text": "x"}, "watermark": {"text": "w"}, "filters": ["user.lua"]}
    with quarto_config_yml(config, tmp_path):
        written = YAML(typ="safe").load(tmp_path / "_quarto.yml")
        user_filter, disclaimer_filter, watermark_filter = written["filters"]
        assert user_filter == "user.lua"
        assert disclaimer_filter["at"] == "pre-ast"
        assert disclaimer_filter["path"].endswith("disclaimer.lua")
        assert watermark_filter["at"] == "post-quarto"
        assert watermark_filter["type"] == "json"
        assert "dso.pandocfilter" in Path(watermark_filter["path"]).read_text()
    # input config is not modified; _quarto.yml and the temporary filter script are cleaned up
    assert config["filters"] == ["user.lua"]
    assert not (tmp_path / "_quarto.yml").exists()
    assert not Path(watermark_filter["path"]).exists()


def test_quarto_config_yml_no_filters(tmp_path):
    """Without disclaimer/watermark (or if they are overridden with null), no filter is registered."""
    for config in [{}, {"disclaimer": None, "watermark": None}, None]:
        with quarto_config_yml(config, tmp_path):
            written = YAML(typ="safe").load(tmp_path / "_quarto.yml") or {}
        assert "filters" not in written


def test_action_watermarks_plotly():
    """A RawBlock containing a plotly plot gets wrapped with the watermark overlay."""
    doc = _doc_with_watermark()
    inner = '<div class="plotly-graph-div" id="abc"></div><script>Plotly.newPlot("abc", []);</script>'
    elem = RawBlock(inner, format="html")

    result = action(elem, doc)

    # original plot html is preserved (incl. the plotly JS) and an overlay is added on top
    assert "plotly-graph-div" in result.text
    assert "Plotly.newPlot" in result.text
    assert "dso-watermark-overlay" in result.text
    assert "pointer-events:none" in result.text


def test_action_watermarks_plotly_htmlwidget():
    """An R plotly (htmlwidgets) RawBlock gets wrapped with the watermark overlay."""
    doc = _doc_with_watermark()
    inner = (
        '<div id="htmlwidget-2abd" style="width:100%;height:900px;" class="plotly html-widget"></div>'
        '<script type="application/json" data-for="htmlwidget-2abd">{"x":{"data":[]}}</script>'
    )
    elem = RawBlock(inner, format="html")

    result = action(elem, doc)

    # original widget html (div + json payload) is preserved and an overlay is added on top
    assert "plotly html-widget" in result.text
    assert 'data-for="htmlwidget-2abd"' in result.text
    assert "dso-watermark-overlay" in result.text
    assert "pointer-events:none" in result.text


def test_action_ignores_non_plotly_rawblock():
    """A RawBlock that is not a plotly plot is left untouched."""
    doc = _doc_with_watermark()
    inner = "<div>just some html</div>"
    elem = RawBlock(inner, format="html")

    result = action(elem, doc)

    assert result.text == inner


def test_action_ignores_plain_text():
    """Non-image, non-RawBlock elements are left untouched."""
    doc = _doc_with_watermark()
    elem = Para(Str("hello"))

    result = action(elem, doc)

    assert result is elem


def test_pandocfilter(quarto_stage):
    copyfile(TESTDATA / "git_logo.png", quarto_stage / "src" / "git_logo.png")
    copyfile(TESTDATA / "git_logo.pdf", quarto_stage / "src" / "git_logo.pdf")
    copyfile(TESTDATA / "git_logo.svg", quarto_stage / "src" / "git_logo.svg")
    copyfile(TESTDATA / "git_logo.svg", quarto_stage / "src" / "git logo.svg")

    # ensure that external files do not get modified inplace
    checksums_before = {}
    for ext in ["png", "pdf", "svg"]:
        with (quarto_stage / "src" / f"git_logo.{ext}").open("rb") as f:
            checksums_before[ext] = hashlib.file_digest(f, "md5").hexdigest()

    quarto_config = YAML(typ="safe").load(
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

    with quarto_config_yml(quarto_config, quarto_stage / "src"):
        render_quarto(
            quarto_stage / "src",
            quarto_stage / "report",
            before_script="",
            cwd=quarto_stage,
        )

    checksums_after = {}
    for ext in ["png", "pdf", "svg"]:
        with (quarto_stage / "src" / f"git_logo.{ext}").open("rb") as f:
            checksums_after[ext] = hashlib.file_digest(f, "md5").hexdigest()

    assert checksums_before == checksums_after

    out_html = (quarto_stage / "report" / "quarto_stage.html").read_text()
    assert "Disclaimer" in out_html
    assert "This is a disclaimer" in out_html
    assert "callout-important" in out_html
    # only present if quarto actually processed the callout
    assert "callout-titled" in out_html


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


def test_disclaimer_typst(quarto_stage):
    """The disclaimer must also be rendered in non-HTML output formats (e.g. typst)"""
    # watermark is enabled to ensure the pandocfilter can handle the raw typst blocks generated by quarto
    quarto_config = {
        "format": {"typst": {"keep-typ": True}},
        "disclaimer": {"title": "Disclaimer", "text": "This is a *disclaimer*"},
        "watermark": {"text": "WATERMARK"},
    }
    (quarto_stage / "src" / "quarto_stage.qmd").write_text("This is a quarto document\n")

    with quarto_config_yml(quarto_config, quarto_stage / "src"):
        render_quarto(
            quarto_stage / "src",
            quarto_stage / "report",
            before_script="",
            cwd=quarto_stage,
        )

    typ_files = list((quarto_stage / "src").glob("*.typ")) + list((quarto_stage / "report").glob("*.typ"))
    assert typ_files
    out_typ = typ_files[0].read_text()
    # rendered as a proper quarto callout
    assert "#callout(" in out_typ
    assert "Disclaimer" in out_typ
    assert "This is a #emph[disclaimer]" in out_typ
