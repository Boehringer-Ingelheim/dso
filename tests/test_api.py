from os import chdir
from pathlib import Path

import pytest
from PIL import Image

import dso
from dso import WatermarkedFile, here, read_params, set_stage, stage_here


def test_api(quarto_stage):
    # reset this to avoid race condition during parallel testing
    dso.api.CONFIG.stage_here = None
    chdir(quarto_stage)

    assert here() == (quarto_stage / "..").resolve()
    assert here("quarto_stage") == quarto_stage

    # stage not yet initialized
    with pytest.raises(RuntimeError):
        stage_here()

    # stage must exist
    with pytest.raises(ValueError):
        set_stage("doesnt/exist")

    set_stage("quarto_stage")

    assert stage_here() == quarto_stage
    assert stage_here("dvc.yaml") == quarto_stage / "dvc.yaml"


def test_api_read_params(quarto_stage):
    # more extensive tests of the same functionality are in `test_get_config.py`
    chdir(quarto_stage)

    params = read_params("quarto_stage")
    assert "dso" in params


@pytest.mark.parametrize("format", ["png", "pdf", "svg"])
def test_watermarked_file(quarto_stage, tmp_path, format):
    """Test that WatermarkedFile context manager produces a watermarked output file."""
    chdir(quarto_stage)
    read_params("quarto_stage")

    output_file = tmp_path / f"output.{format}"

    with WatermarkedFile(output_file, text="DRAFT") as f:
        if format == "svg":
            Path(f).write_text(
                '<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100"><rect width="100" height="100"/></svg>'
            )
        elif format == "pdf":
            # Create a minimal valid PDF
            from pypdf import PdfWriter

            writer = PdfWriter()
            writer.add_blank_page(width=200, height=200)
            writer.write(f)
        else:
            img = Image.new("RGB", (100, 100), color=(73, 109, 137))
            img.save(f)

    assert output_file.exists()
    assert output_file.stat().st_size > 0
