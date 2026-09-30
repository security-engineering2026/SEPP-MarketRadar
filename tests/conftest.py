import os
import sys
from pathlib import Path
import pytest
import importlib
import importlib.util

REPO_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT_STR = str(REPO_ROOT)
PACKAGE_ROOT = REPO_ROOT / "marketradar"

# The environment has a shadowed/stale installed marketradar package. Do not
# rely on sys.path precedence alone: pytest must execute the repository package.
for _name in list(sys.modules):
    if _name == "marketradar" or _name.startswith("marketradar."):
        del sys.modules[_name]

for _entry in list(sys.path):
    try:
        if Path(_entry or ".").resolve() == REPO_ROOT:
            sys.path.remove(_entry)
    except (OSError, RuntimeError):
        pass
sys.path.insert(0, REPO_ROOT_STR)
importlib.invalidate_caches()

_package_init = PACKAGE_ROOT / "__init__.py"
_package_spec = importlib.util.spec_from_file_location(
    "marketradar",
    _package_init,
    submodule_search_locations=[str(PACKAGE_ROOT)],
)
if _package_spec is None or _package_spec.loader is None:
    raise ImportError(f"Cannot load repository marketradar package from {_package_init}")
_package = importlib.util.module_from_spec(_package_spec)
sys.modules["marketradar"] = _package
_package_spec.loader.exec_module(_package)

# Preload the Row 4 module from the repository path as an invariant. This
# prevents a globally installed/shadowed source_verification module from
# replacing the implementation under test.
_source_path = PACKAGE_ROOT / "source_verification.py"
_source_spec = importlib.util.spec_from_file_location(
    "marketradar.source_verification",
    _source_path,
)
if _source_spec is None or _source_spec.loader is None:
    raise ImportError(f"Cannot load repository source_verification from {_source_path}")
_source_module = importlib.util.module_from_spec(_source_spec)
sys.modules["marketradar.source_verification"] = _source_module
_source_spec.loader.exec_module(_source_module)

if Path(_source_module.__file__).resolve() != _source_path.resolve():
    raise ImportError(
        "Row 4 import isolation failed: "
        f"expected {_source_path.resolve()}, got {Path(_source_module.__file__).resolve()}"
    )
if not all(hasattr(_source_module.SourceVerificationEngine, _name) for _name in (
    "_one",
    "persist",
    "_policy_fetch_fallback",
)):
    raise ImportError(
        "Repository source_verification.py does not expose the Row 4 implementation "
        "required by the focused verification tests"
    )

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
