from __future__ import annotations
from pathlib import Path
from .finance import period_report, export_report

def generate_all(c, out_dir: Path, when=None):
    out={}
    for p in ('weekly','monthly','quarterly','annual'):
        r=period_report(c,p,when); out[p]=export_report(c,r,out_dir)
    return out
