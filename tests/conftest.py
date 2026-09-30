import os
import sys
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

@pytest.fixture(scope="session", autouse=True)
def isolate_market_radar_runtime(tmp_path_factory):
    root = tmp_path_factory.mktemp("marketradar-runtime")
    old = os.environ.get("MARKETRADAR_DATA_ROOT")
    os.environ["MARKETRADAR_DATA_ROOT"] = str(root)
    try:
        yield
    finally:
        if old is None:
            os.environ.pop("MARKETRADAR_DATA_ROOT", None)
        else:
            os.environ["MARKETRADAR_DATA_ROOT"] = old
