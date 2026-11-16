import base64
import hashlib
import json
import urllib.parse
from os import chdir
from pathlib import Path
from shutil import copyfile
from textwrap import dedent

import panflute.elements
import pytest
from click.testing import CliRunner
from panflute import Doc, Image, MetaMap, MetaString, Para, RawBlock, Str

from dso._quarto import render_quarto
from dso.cli import dso_exec
from dso.pandocfilter import _get_watermark_dir, action
from tests.conftest import TESTDATA


def _doc_with_watermark(text="WATERMARK"):
    """Build a minimal panflute Doc carrying a watermark config in its metadata."""
    return Doc(metadata=MetaMap(watermark=MetaMap(text=MetaString(text))))


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


def _quarto_filter_params(**params):
    return base64.b64encode(json.dumps(params).encode()).decode()


@pytest.mark.parametrize(
    "env,expected",
    [
        (None, None),
        ("", None),
        ("not-base64-json", None),
        (_quarto_filter_params(), None),
        (_quarto_filter_params(**{"mediabag-dir": "doc_files/mediabag"}), Path("doc_files/mediabag")),
    ],
)
def test_get_watermark_dir(monkeypatch, env, expected):
    if env is None:
        monkeypatch.delenv("QUARTO_FILTER_PARAMS", raising=False)
    else:
        monkeypatch.setenv("QUARTO_FILTER_PARAMS", env)
    assert _get_watermark_dir() == expected


def test_action_watermarks_image_in_mediabag(tmp_path, monkeypatch):
    """Watermarked images are written to the quarto mediabag dir (relative path), the original is untouched."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("QUARTO_FILTER_PARAMS", _quarto_filter_params(**{"mediabag-dir": "doc_files/mediabag"}))
    copyfile(TESTDATA / "git_logo.svg", tmp_path / "git logo.svg")
    original = (tmp_path / "git logo.svg").read_bytes()
    doc = _doc_with_watermark()
    elem = Image(url="git%20logo.svg")

    result = action(elem, doc)

    out_path = Path(urllib.parse.unquote(result.url))
    assert not out_path.is_absolute()
    assert out_path.parent == Path("doc_files/mediabag")
    assert out_path.name.startswith("git logo.wm.")
    assert out_path.suffix == ".svg"
    assert "WATERMARK" in out_path.read_text()
    assert (tmp_path / "git logo.svg").read_bytes() == original
    # nothing else was written to the document directory
    assert sorted(p.name for p in tmp_path.iterdir()) == ["doc_files", "git logo.svg"]


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

    checksums_after = {}
    for ext in ["png", "pdf", "svg"]:
        with (quarto_stage / "src" / f"git_logo.{ext}").open("rb") as f:
            checksums_after[ext] = hashlib.file_digest(f, "md5").hexdigest()

    assert checksums_before == checksums_after

    out_html = (quarto_stage / "report" / "quarto_stage.html").read_text()
    assert "Disclaimer" in out_html
    assert "This is a disclaimer" in out_html
    assert "callout-important" in out_html


@pytest.mark.skipif(
    "typst" not in panflute.elements.RAW_FORMATS,
    reason="installed panflute version does not support raw typst (sergiocorreia/panflute#265)",
)
def test_pandocfilter_typst(quarto_stage):
    """Watermarked images must be within the project directory, otherwise typst can't read them (#193)"""
    src = quarto_stage / "src"
    for ext in ["png", "svg"]:
        copyfile(TESTDATA / f"git_logo.{ext}", src / f"git_logo.{ext}")
    (src / "_quarto.yml").write_text(
        dedent(
            """\
            format: typst
            watermark:
                text: WATERMARK
            """
        )
    )
    (src / "quarto_stage.qmd").write_text("![PNG Image](git_logo.png)\n\n![SVG Image](git_logo.svg)\n")

    def _project_files():
        # ignore the rendered report and quarto's own cache
        return {
            p: p.read_bytes()
            for p in quarto_stage.rglob("*")
            if p.is_file() and not {"report", ".quarto"} & set(p.relative_to(quarto_stage).parts)
        }

    files_before = _project_files()

    render_quarto(src, quarto_stage / "report", before_script="", cwd=quarto_stage, with_pandocfilter=True)

    assert (quarto_stage / "report" / "quarto_stage.pdf").exists()
    # original files are not modified and no leftover files are written into the project
    assert _project_files() == files_before


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
