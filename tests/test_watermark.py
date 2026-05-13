from typing import Literal

import pytest
from click.testing import CliRunner
from PIL import Image

from dso._watermark import PDFWatermarker, SVGWatermarker, Watermarker
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
