import os
import tempfile
from pathlib import Path

from marketradar.logging_setup import configure_logging, close_logging


def test_logging_handler_can_release_temporary_data_root():
    old = os.environ.get("MARKETRADAR_DATA_ROOT")
    with tempfile.TemporaryDirectory() as d:
        os.environ["MARKETRADAR_DATA_ROOT"] = d
        logger = configure_logging()
        logger.info("windows logging cleanup regression")
        close_logging()
        assert not any(getattr(h, "stream", None) is not None for h in logger.handlers)
    if old is None:
        os.environ.pop("MARKETRADAR_DATA_ROOT", None)
    else:
        os.environ["MARKETRADAR_DATA_ROOT"] = old
