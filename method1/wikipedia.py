#!/usr/bin/env python3


from __future__ import annotations

import argparse
import json
import random
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup

_TOC_NUMBER_RE = re.compile(r"^\d+(?:\.\d+)*")
_LAST_EDITED_RE = re.compile(
    r"last edited on\s+(.+?)(?:\s*\(UTC\)|\s*UTC)?\.?$", re.I
)


def extract_url_from_html(file_path: str) -> str:

    try:
        with open(file_path, encoding="utf-8") as fh:
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
        pass
    return ""


def _clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("\xa0", " ")).strip()


def _first_paragraph(soup: BeautifulSoup) -> str | None:
    body = soup.find(id="mw-content-text")
    if not body:
        return None

    for paragraph in body.find_all("p", recursive=True):
        text = _clean_text(paragraph.get_text(" ", strip=True))
        if len(text) < 40:
            continue
        if text.lower().startswith("coordinates:"):
            continue
        if text.startswith("This article"):
            continue
        return text
    return None


def _infobox_facts(soup: BeautifulSoup) -> list[str]:
    infobox = soup.find("table", class_="infobox")
    if not infobox:
        return []

    facts: list[str] = []
    seen: set[str] = set()
    for row in infobox.find_all("tr"):
        header = row.find("th")
        cell = row.find("td")
        if not header or not cell:
            continue
        label = _clean_text(header.get_text(" ", strip=True))
        value = _clean_text(cell.get_text(" ", strip=True))
        if not label or not value:
            continue
        if label.startswith("•"):
            label = label.lstrip("• ").strip()
        fact = f"{label}: {value}"
        if fact not in seen and len(value) <= 300:
            seen.add(fact)
            facts.append(fact)
    return facts


def _normalize_toc_item(text: str) -> str:
    cleaned = _TOC_NUMBER_RE.sub("", text).strip()
    return cleaned or text.strip()


def _table_of_contents(soup: BeautifulSoup) -> list[str]:
    items: list[str] = []
    seen: set[str] = set()

    panel_toc = soup.select_one("#mw-panel-toc")
    if panel_toc:
        for link in panel_toc.select("a"):
            text = _normalize_toc_item(link.get_text(" ", strip=True))
            if not text or text.lower() in {"(top)", "top"}:
                continue
            if text not in seen:
                seen.add(text)
                items.append(text)
        if items:
            return items

    legacy_toc = soup.find(id="toc")
    if legacy_toc:
        for link in legacy_toc.select("a"):
            text = _normalize_toc_item(link.get_text(" ", strip=True))
            if text and text not in seen:
                seen.add(text)
                items.append(text)
        if items:
            return items

    body = soup.find(id="mw-content-text")
    if body:
        for heading in body.find_all(["h2", "h3"]):
            span = heading.find("span", class_="mw-headline")
            text = _clean_text(
                span.get_text(" ", strip=True) if span else heading.get_text(" ", strip=True)
            )
            if text and text not in seen:
                seen.add(text)
                items.append(text)
    return items


def _last_edited_date(soup: BeautifulSoup) -> str | None:
    footer = soup.find(id="footer-info-lastmod")
    if not footer:
        return None
    text = _clean_text(footer.get_text(" ", strip=True))
    match = _LAST_EDITED_RE.search(text)
    if match:
        return _clean_text(match.group(1))
    if "last edited on" in text.lower():
        return text.split("last edited on", 1)[-1].strip(" .")
    return text or None


def scrape_wikipedia_html(html_path: str) -> dict[str, Any]:
    with open(html_path, encoding="utf-8", errors="replace") as fh:
        soup = BeautifulSoup(fh.read(), "html.parser")

    title_el = soup.find(id="firstHeading")

    return {
        "article_title": title_el.get_text(" ", strip=True) if title_el else None,
        "first_paragraph": _first_paragraph(soup),
        "infobox_key_facts": _infobox_facts(soup),
        "table_of_contents": _table_of_contents(soup),
        "last_edited_date": _last_edited_date(soup),
    }


def _process_file(file_path: str) -> dict:
    result = {
        "filename": Path(file_path).name,
        "full_path": str(Path(file_path).resolve()),
        "url": extract_url_from_html(file_path),
        "status": "failed",
        "error": None,
        "extracted_data": None,
    }
    try:
        result["extracted_data"] = scrape_wikipedia_html(file_path)
        result["status"] = "success"
    except Exception as e:
        result["error"] = str(e)
    return result


def run_batch(directory: str, num_files: int, max_workers: int = 5) -> dict:
    dir_path = Path(directory)
    html_files = list(dir_path.glob("*.html"))
    if not html_files:
        raise FileNotFoundError(f"No HTML files in {directory}")

    n = min(num_files, len(html_files))
    selected = [str(p) for p in random.sample(html_files, n)]

    processed = []
    with ThreadPoolExecutor(max_workers=min(max_workers, n)) as pool:
        futures = {pool.submit(_process_file, path): path for path in selected}
        for fut in as_completed(futures):
            processed.append(fut.result())

    successful = sum(1 for r in processed if r["status"] == "success")
    return {
        "processed_files": processed,
        "summary": {
            "total_requested": num_files,
            "total_processed": len(processed),
            "successful": successful,
            "failed": len(processed) - successful,
            "directory": str(dir_path.resolve()),
            "max_workers": max_workers,
            "site": "wikipedia.org",
        },
    }


def main():
    parser = argparse.ArgumentParser(description="Wikipedia article scraper (BeautifulSoup)")
    parser.add_argument("-d", "--directory", required=True, help="Folder of saved .html files")
    parser.add_argument("-n", "--num-files", type=int, required=True, help="Random sample count")
    parser.add_argument("-o", "--output", default="results.json", help="Output JSON path")
    parser.add_argument("-w", "--max-workers", type=int, default=5, help="Parallel workers")
    args = parser.parse_args()

    results = run_batch(args.directory, args.num_files, args.max_workers)
    with open(args.output, "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=2, ensure_ascii=False)

    s = results["summary"]
    print(f"Done: {s['successful']}/{s['total_processed']} successful → {args.output}")


if __name__ == "__main__":
    main()
