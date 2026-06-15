from typing import Literal

import pytest
from click.testing import CliRunner
from PIL import Image

from dso._watermark import PDFWatermarker, SVGWatermarker, Watermarker, get_plotly_watermark_html
from dso.cli import dso_watermark
from tests.conftest import TESTDATA


def _get_test_image(tmp_path, *, img_name="test_image", format: Literal["png", "jpg"], size=(500, 500)):
    img = Image.new("RGB", size, color=(73, 109, 137))
    path = tmp_path / f"{img_name}.{format}"
    img.save(path)
    return path


@pytest.mark.parametrize("format", ["png", "jpg"])
@pytest.mark.parametrize("tile_size", [(20, 20), (20, 200), (200, 20), (200, 200)])
@pytest.mark.parametrize("image_size", [(100, 100), (500, 500), (2000, 200)])
@pytest.mark.parametrize("font_size", [14, 200])
def test_add_watermark(tmp_path, format, tile_size, image_size, font_size):
    test_image = _get_test_image(tmp_path, format=format, size=image_size)
    test_image_out = tmp_path / f"test_image_out.{format}"
    Watermarker.add_watermark(test_image, test_image_out, text="test", tile_size=tile_size, font_size=font_size)


def test_add_watermark_svg(tmp_path):
    wm = SVGWatermarker("test")
    wm.apply_and_save(TESTDATA / "git_logo.svg", tmp_path / "git_logo_watermarked.svg")


def test_get_tile_svg():
    """The tile SVG is a standalone, tile-sized SVG document containing the watermark text twice."""
    import xml.etree.ElementTree as ET

    wm = SVGWatermarker("WMTEXT", tile_size=(120, 80))
    svg = wm.get_tile_svg()

    # parses as valid XML
    root = ET.fromstring(svg)
    assert root.tag == "{http://www.w3.org/2000/svg}svg"
    assert root.get("width") == "120"
    assert root.get("height") == "80"

    texts = root.findall("{http://www.w3.org/2000/svg}text")
    assert len(texts) == 2
    assert all(t.text == "WMTEXT" for t in texts)


def test_get_plotly_watermark_html():
    """The plotly watermark wraps the original html in an overlay that sits on top but ignores pointer events."""
    inner = '<div class="plotly-graph-div" id="abc"></div>'
    out = get_plotly_watermark_html(inner, text="WMTEXT", tile_size=(120, 80))

    # original plot html is preserved
    assert inner in out
    # overlay sits above the plot but does not block hover/tooltips
    assert "pointer-events:none" in out
    assert "z-index:1000" in out
    # watermark is provided as a repeating, tile-sized SVG background
    assert "data:image/svg+xml;base64," in out
    assert "background-repeat:repeat" in out
    assert "background-size:120px 80px" in out
    # plotly's download button is hidden so users can't grab an un-watermarked copy
    assert '.modebar-btn[data-title*="download" i]' in out
    assert "display:none" in out


@pytest.mark.parametrize(
    "pdf_file",
    [
        "git_logo.pdf",  # single page, pixel
        "lorem_ipsum.pdf",  # multi page, vector
    ],
)
def test_add_watermark_pdf(tmp_path, pdf_file):
    wm = PDFWatermarker("test")
    wm.apply_and_save(TESTDATA / pdf_file, tmp_path / pdf_file)


@pytest.mark.parametrize(
    "text, expected",
    [
        # Printable ASCII passes through unchanged
        ("hello world", "hello world"),
        # Named escapes
        ("back\\slash", "back\\\\slash"),
        ("left(paren", "left\\(paren"),
        ("right)paren", "right\\)paren"),
        ("new\nline", "new\\nline"),
        ("carriage\rreturn", "carriage\\rreturn"),
        ("hori\tzontal", "hori\\tzontal"),
        ("back\bspace", "back\\bspace"),
        ("form\ffeed", "form\\ffeed"),
        # Non-ASCII encoded as WinAnsiEncoding (cp1252) octal sequences
        # 'é' → cp1252 byte 0xE9 → \351
        ("café", "caf\\351"),
        # '€' → cp1252 byte 0x80 → \200
        ("€1", "\\2001"),
        # German umlauts
        ("äöü", "\\344\\366\\374"),
        # Combination: parens + non-ASCII
        ("(café)", "\\(caf\\351\\)"),
    ],
)
def test_pdf_escape(text, expected):
    assert PDFWatermarker._pdf_escape(text) == expected


@pytest.mark.parametrize(
    "params",
    [
        [],
        [
            "--tile_size",
            "20",
            "20",
            "--font_size",
            "20",
            "--font_outline",
            "2",
            "--font_color",
            "black",
            "--font_outline_color",
            "white",
        ],
    ],
)
def test_add_watermark_cli(tmp_path, params):
    runner = CliRunner()
    test_image = _get_test_image(tmp_path, format="png", size=(500, 500))
    test_image_out = tmp_path / "test_image_out.png"

    result = runner.invoke(dso_watermark, [str(test_image), str(test_image_out), "--text", "test text", *params])
    assert result.exit_code == 0
    assert test_image_out.is_file()
