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

_HOURLY_RATE_RE = re.compile(r"\$[\d,]+(?:\.\d+)?/hr", re.I)


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


def _freelancer_name(soup: BeautifulSoup) -> str | None:
    for h2 in soup.find_all("h2"):
        name = h2.get_text(" ", strip=True)
        if name and name.lower() not in {"this site uses cookies"}:
            return re.sub(r"\s+", " ", name).strip()
    return None


def _hourly_rate(soup: BeautifulSoup) -> str | None:
    profile = soup.select_one(".cfe-ui-profile-summary") or soup.select_one(".air3-card-sections")
    search_roots = [profile, soup]
    for root in search_roots:
        if not root:
            continue
        match = _HOURLY_RATE_RE.search(root.get_text(" ", strip=True))
        if match:
            return match.group(0)
    return None


def _profile_stats(soup: BeautifulSoup) -> tuple[str | None, str | None]:
    stats_block = soup.select_one(".cfe-ui-profile-summary-stats")
    if not stats_block:
        return None, None

    jobs_completed = hours_worked = None
    for col in stats_block.select(".col-compact"):
        amount_el = col.select_one(".stat-amount")
        label_el = col.select_one(".text-base-sm")
        if not amount_el or not label_el:
            continue
        label = label_el.get_text(" ", strip=True).lower()
        value = amount_el.get_text(" ", strip=True)
        if "total jobs" in label:
            jobs_completed = value
        elif "total hours" in label:
            hours_worked = value
    return jobs_completed, hours_worked


def _profile_description(soup: BeautifulSoup) -> str | None:
    clamp = soup.select_one(".air3-line-clamp")
    if not clamp:
        return None

    text = clamp.get_text("\n", strip=True)
    if not text:
        return None

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return None

    tagline = None
    for h2 in soup.find_all("h2"):
        candidate = h2.get_text(" ", strip=True)
        if candidate and candidate.lower() != "this site uses cookies":
            if tagline is None and candidate != lines[0]:
                tagline = candidate
            elif tagline is None:
                tagline = None
            break

    if len(lines) > 1:
        first = lines[0]
        if "|" in first or (tagline and first == tagline) or len(first) < 120:
            body = "\n".join(lines[1:]).strip()
            if body:
                return body

    return text


def scrape_upwork_html(html_path: str) -> dict[str, Any]:
    with open(html_path, encoding="utf-8", errors="replace") as fh:
        soup = BeautifulSoup(fh.read(), "html.parser")

    jobs_completed, hours_worked = _profile_stats(soup)

    return {
        "freelancer_name": _freelancer_name(soup),
        "hourly_rate": _hourly_rate(soup),
        "full_profile_description": _profile_description(soup),
        "number_of_jobs_completed": jobs_completed,
        "total_hours_worked": hours_worked,
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
        result["extracted_data"] = scrape_upwork_html(file_path)
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
            "site": "upwork.com",
        },
    }


def main():
    parser = argparse.ArgumentParser(description="Upwork profile scraper (BeautifulSoup)")
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
