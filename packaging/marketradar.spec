# PyInstaller spec for the Windows desktop product.
from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules

ROOT = Path(SPECPATH).resolve().parent
hiddenimports = collect_submodules("marketradar") + collect_submodules("tools")

a = Analysis(
    [str(ROOT / "desktop" / "MarketRadar.pyw")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[
        (str(ROOT / "config"), "config"),
    ],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["pytest"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="MarketRadar",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
)
