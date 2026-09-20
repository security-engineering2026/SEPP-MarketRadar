from __future__ import annotations
import os
import sys
from pathlib import Path

APP_NAME = "SEPP-MarketRadar"

def app_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]

def is_portable() -> bool:
    return os.environ.get("MARKETRADAR_PORTABLE") == "1" or (app_root() / ".portable").is_file()

def writable_root() -> Path:
    override = os.environ.get('MARKETRADAR_DATA_ROOT')
    if override:
        root = Path(override).expanduser()
        root.mkdir(parents=True, exist_ok=True)
        return root
    if is_portable():
        root = app_root()
    elif sys.platform == "win32":
        local = os.environ.get("LOCALAPPDATA")
        root = Path(local) / APP_NAME if local else Path.home() / "AppData" / "Local" / APP_NAME
    else:
        local = os.environ.get("XDG_DATA_HOME")
        root = Path(local) / APP_NAME if local else Path.home() / ".local" / "share" / APP_NAME
    root.mkdir(parents=True, exist_ok=True)
    return root

def data_root() -> Path:
    root = writable_root() / "data"; root.mkdir(parents=True, exist_ok=True); return root

def log_root() -> Path:
    root = writable_root() / "logs"; root.mkdir(parents=True, exist_ok=True); return root
