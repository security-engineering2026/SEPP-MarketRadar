from __future__ import annotations

import os
import time
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PIL import ImageGrab
import tkinter as tk

from marketradar.desktop import MarketRadarDesktop

out = Path(os.environ.get("QUALIFICATION_ARTIFACT_DIR", "qualification-artifacts"))
out.mkdir(parents=True, exist_ok=True)

root = tk.Tk()
app = None
try:
    root.withdraw()
    app = MarketRadarDesktop(root)
    root.deiconify()
    root.update_idletasks()
    root.update()
    time.sleep(1)
    left = root.winfo_rootx()
    top = root.winfo_rooty()
    right = left + root.winfo_width()
    bottom = top + root.winfo_height()
    image = ImageGrab.grab(bbox=(left, top, right, bottom), all_screens=True)
    target = out / "ui-main-window.png"
    image.save(target)
    if image.width < 900 or image.height < 600:
        raise RuntimeError(f"UI_SCREENSHOT_TOO_SMALL:{image.width}x{image.height}")
    print(f"UI_VISUAL_SMOKE=PASS path={target} size={image.width}x{image.height}")
finally:
    try:
        if app:
            app.close()
        else:
            root.destroy()
    except Exception:
        root.destroy()
