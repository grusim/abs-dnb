from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


def _load(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


@pytest.fixture
def fixture_bytes():
    return _load


@pytest.fixture
def leises_gift():
    return _load("leises-gift.xml")


@pytest.fixture
def saeulen():
    return _load("saeulen.xml")


@pytest.fixture
def tintenherz():
    return _load("tintenherz.xml")


@pytest.fixture
def vorleser():
    return _load("vorleser.xml")
