from os import chdir

import pytest

from dso import here, read_params, set_stage, stage_here


def test_api(quarto_stage):
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
