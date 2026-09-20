# Windows Release Candidate Fix

GitHub Windows Release validation reached the PyInstaller build and failed because `packaging/marketradar.spec` resolved `SPECPATH` one directory too high.

The spec now resolves the repository root with:

```python
ROOT = Path(SPECPATH).resolve().parent
```

The existing repository validation HEAD expected by the sync script is `e317560`, the commit that produced the observed release-validation failure.
