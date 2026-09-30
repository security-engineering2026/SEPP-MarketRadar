import os
import sys
from pathlib import Path
import pytest
import importlib

# Purge any preloaded third-party/local-shadowed marketradar modules before tests import them.
for _name in list(sys.modules):
    if _name == "marketradar" or _name.startswith("marketradar."):
        del sys.modules[_name]
importlib.invalidate_caches()

REPO_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT_STR = str(REPO_ROOT)

# Normalize sys.path entries before forcing the repository root to the front.
for _entry in list(sys.path):
    try:
        if Path(_entry or ".").resolve() == REPO_ROOT:
            sys.path.remove(_entry)
    except (OSError, RuntimeError):
        pass
sys.path.insert(0, REPO_ROOT_STR)

# Purge again after path correction so any preloaded shadow package cannot survive.
for _name in list(sys.modules):
    if _name == "marketradar" or _name.startswith("marketradar."):
        del sys.modules[_name]
importlib.invalidate_caches()

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
