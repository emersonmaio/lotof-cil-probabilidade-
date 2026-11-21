import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import pytest


@pytest.fixture(scope="session")
def root():
    return ROOT


@pytest.fixture(scope="session")
def csv_path(root):
    return str(root / "data" / "lotofacil.csv")


@pytest.fixture(scope="session")
def history(csv_path):
    from data_io import load_history
    return load_history(csv_path)
