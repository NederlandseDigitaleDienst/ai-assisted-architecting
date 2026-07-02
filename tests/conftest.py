import shutil
from pathlib import Path

import pytest

from archi_tool.model import ArchiModel

FIXTURE = Path(__file__).parent / "fixtures" / "klein-model.archimate"


@pytest.fixture
def model_path(tmp_path):
    path = tmp_path / "model.archimate"
    shutil.copy(FIXTURE, path)
    return path


@pytest.fixture
def model(model_path):
    return ArchiModel(model_path)
