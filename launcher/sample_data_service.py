from __future__ import annotations

import random
import re
import shutil
import tempfile
from pathlib import Path
from urllib.parse import urlparse

from launcher.project_tmp import TMP_DIR


def normalize_url(url: str) -> str:

    if not url:
        return ""
    url = url.strip().rstrip("/")
    url = url.split("#", 1)[0].split("?", 1)[0]
    return url.lower()


def _extract_saved_url(html_path: Path) -> str:
    try:
        with html_path.open(encoding="utf-8", errors="replace") as fh:
            for _ in range(10):
                line = fh.readline()
                if not line:
                    break
                if "saved from url=" not in line:
                    continue
                match = re.search(r"url=\(\d+\)(https?://[^)]+?)(?:\s*-->)", line)
                if match:
                    return match.group(1)
                match = re.search(r"(https?://[^\s>]+?)(?:\s*-->)", line)
                if match:
                    return match.group(1)
    except OSError:
        return ""
    return ""


def site_folder_for_url(url: str, sample_root: Path) -> Path | None:

    root = Path(sample_root)
    if not root.is_dir():
        return None

    host = urlparse(url).netloc.lower().replace("www.", "")
    candidates = [
        root / host,
        root / host.replace(".", "-"),
        root / host.split(".")[0],
    ]
    seen = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        if candidate.is_dir() and any(candidate.glob("*.html")):
            return candidate
    return None


def find_html_for_url(url: str, sample_root: Path) -> Path | None:

    site_dir = site_folder_for_url(url, sample_root)
    if site_dir is None:
        return None

    target = normalize_url(url)
    for html_path in sorted(site_dir.glob("*.html")):
        saved = normalize_url(_extract_saved_url(html_path))
        if saved and saved == target:
            return html_path
    return None


def prepare_html_workspace(html_path: Path) -> str:


    html_path = Path(html_path).resolve()
    work_dir = Path(tempfile.mkdtemp(prefix="sample_", dir=str(TMP_DIR)))
    dest_html = work_dir / html_path.name
    shutil.copy2(html_path, dest_html)

    assets_dir = html_path.parent / f"{html_path.stem}_files"
    if assets_dir.is_dir():
        shutil.copytree(assets_dir, work_dir / assets_dir.name)

    return str(work_dir)


def prepare_sample_workspace(directory: str, num_files: int) -> tuple[str, list[str]]:


    dir_path = Path(directory).resolve()
    html_files = sorted(dir_path.glob("*.html"))
    if not html_files:
        raise FileNotFoundError(f"No HTML files in {directory}")

    n = min(num_files, len(html_files))
    selected = random.sample(html_files, n)

    work_dir = Path(tempfile.mkdtemp(prefix="batch_", dir=str(TMP_DIR)))
    copied = []
    for html_path in selected:
        dest_html = work_dir / html_path.name
        shutil.copy2(html_path, dest_html)
        assets_dir = html_path.parent / f"{html_path.stem}_files"
        if assets_dir.is_dir():
            dest_assets = work_dir / assets_dir.name
            if not dest_assets.exists():
                shutil.copytree(assets_dir, dest_assets)
        copied.append(str(dest_html))

    return str(work_dir), copied
