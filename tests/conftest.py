import os

import pytest

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


@pytest.fixture
def sample_nda_path() -> str:
    return os.path.join(FIXTURES, "sample_nda.txt")
