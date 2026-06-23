import hashlib
import os
import re

from config import settings
from utils.logging_utils import tprint


def safe_filename(url: str) -> str:

    h = hashlib.md5(url.encode("utf-8")).hexdigest()[:10]
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", url.split("://")[-1])[:80].strip("-")
    return f"{slug or 'page'}-{h}.html"


def save_html(url: str, domain: str, html: str) -> str | None:

    if not settings.HTML_OUTPUT_DIR:
        return None
    domain_dir = os.path.join(settings.HTML_OUTPUT_DIR, domain)
    try:
        os.makedirs(domain_dir, exist_ok=True)
        path = os.path.join(domain_dir, safe_filename(url))
        url_comment = f"<!-- saved from url=({len(url):04d}){url} -->\n"
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(url_comment + html)
        tprint(f"  [{domain}] HTML saved → {path}")
        return path
    except Exception as e:
        tprint(f"  [{domain}] ⚠ failed to save HTML: {e}")
        return None
