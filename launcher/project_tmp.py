from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TMP_DIR = ROOT / "results" / "tmp"


def ensure_tmp_dir() -> Path:

    TMP_DIR.mkdir(parents=True, exist_ok=True)
    path = str(TMP_DIR)
    os.environ["TMPDIR"] = path
    os.environ["TEMP"] = path
    os.environ["TMP"] = path
    return TMP_DIR
