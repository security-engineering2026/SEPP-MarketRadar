from __future__ import annotations
import logging
import sys
import atexit
from logging.handlers import RotatingFileHandler
from pathlib import Path
from .paths import log_root

LOGGER_NAME = "marketradar"


def _file_handlers(logger: logging.Logger):
    return [h for h in logger.handlers if isinstance(h, RotatingFileHandler)]


def _handler_path(handler) -> Path | None:
    raw = getattr(handler, "baseFilename", None)
    if not raw:
        return None
    try:
        return Path(raw).resolve()
    except OSError:
        return Path(raw)


def close_logging() -> None:
    """Release MarketRadar log file handles, especially important on Windows."""
    logger = logging.getLogger(LOGGER_NAME)
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        try:
            handler.flush()
        finally:
            handler.close()


def configure_logging() -> logging.Logger:
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(logging.INFO)
    desired = (log_root() / "marketradar.log").resolve()

    # Tests and portable runs can change MARKETRADAR_DATA_ROOT between app instances.
    # Never keep a handler attached to an old temporary directory: Windows would
    # otherwise refuse to remove that directory while the file handle is open.
    for handler in list(_file_handlers(logger)):
        if _handler_path(handler) != desired:
            logger.removeHandler(handler)
            handler.close()

    if not any(_handler_path(h) == desired for h in _file_handlers(logger)):
        handler = RotatingFileHandler(
            desired, maxBytes=2_000_000, backupCount=3, encoding="utf-8"
        )
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
        logger.addHandler(handler)

    if not any(isinstance(h, logging.StreamHandler) and not isinstance(h, RotatingFileHandler) for h in logger.handlers):
        if not getattr(sys, "frozen", False):
            console = logging.StreamHandler()
            console.setFormatter(logging.Formatter("%(levelname)s %(message)s"))
            logger.addHandler(console)
    logger.propagate = False
    return logger


def install_exception_logging(root=None) -> None:
    logger = configure_logging()

    def hook(exc_type, exc_value, exc_tb):
        logger.critical("Unhandled exception", exc_info=(exc_type, exc_value, exc_tb))
        if not getattr(sys, "frozen", False):
            sys.__excepthook__(exc_type, exc_value, exc_tb)

    sys.excepthook = hook
    if root is not None:
        def tk_hook(exc, val, tb):
            logger.critical("Unhandled GUI callback exception", exc_info=(exc, val, tb))
        root.report_callback_exception = tk_hook


atexit.register(close_logging)
