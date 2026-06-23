#!/usr/bin/env python3


from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from urllib.parse import urlparse, urlunparse

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = REPO_ROOT / "urls" / "yahoo.finance.com.txt"
DEFAULT_DIR = Path.home() / "Downloads"

SAVED_URL_RE = re.compile(r"url=\(\d+\)(https?://[^)\s]+)")


def canonical_quote_url(raw: str) -> str | None:
    parsed = urlparse(raw.strip())
    if "/quote/" not in parsed.path:
        return None
    path = parsed.path.rstrip("/") + "/"
    return urlunparse((parsed.scheme, parsed.netloc, path, "", "", ""))


def extract_url_from_html(path: Path) -> str | None:
    head = path.read_text(encoding="utf-8", errors="replace")[:8000]
    match = SAVED_URL_RE.search(head)
    if not match:
        return None
    return canonical_quote_url(match.group(1))


def collect_urls(html_dir: Path) -> tuple[list[str], list[str]]:
    urls: list[str] = []
    seen: set[str] = set()
    skipped: list[str] = []

    files = sorted(
        p
        for p in html_dir.iterdir()
        if p.is_file()
        and p.suffix.lower() == ".html"
        and "yahoo" in p.name.lower()
        and "finance" in p.name.lower()
    )

    for path in files:
        raw = extract_url_from_html(path)
        if not raw:
            skipped.append(path.name)
            continue
        if raw in seen:
            continue
        seen.add(raw)
        urls.append(raw)

    return urls, skipped


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "html_dir",
        nargs="?",
        type=Path,
        default=DEFAULT_DIR,
        help=f"Folder with saved Yahoo Finance HTML (default: {DEFAULT_DIR})",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=DEFAULT_OUT,
        help=f"Output URL list (default: {DEFAULT_OUT})",
    )
    args = parser.parse_args()

    html_dir = args.html_dir.expanduser().resolve()
    if not html_dir.is_dir():
        print(f"Error: not a directory: {html_dir}", file=sys.stderr)
        return 1

    urls, skipped = collect_urls(html_dir)
    if not urls:
        print(f"Error: no quote URLs found in {html_dir}", file=sys.stderr)
        return 1

    out_path = args.output.expanduser().resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(urls) + "\n", encoding="utf-8")

    print(f"Scanned {html_dir}")
    print(f"Wrote {len(urls)} URLs → {out_path}")
    if skipped:
        print(f"Skipped {len(skipped)} non-quote page(s):")
        for name in skipped:
            print(f"  - {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
