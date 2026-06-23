#!/usr/bin/env python3


from __future__ import annotations

import argparse
import json
import random
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup


def _split_datetime(iso: str) -> tuple[str | None, str | None]:

    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d"), dt.strftime("%H:%M:%S %Z")
    except ValueError:
        return None, None


def scrape_reuters_html(html_path: str) -> dict[str, Any]:
    with open(html_path, encoding="utf-8", errors="replace") as fh:
        soup = BeautifulSoup(fh.read(), "html.parser")


    headline_el = soup.find("h1", attrs={"data-testid": "Heading"})
    headline = headline_el.get_text(" ", strip=True) if headline_el else None


    author_el = soup.find(attrs={"data-testid": "AuthorName"})
    author = author_el.get_text(" ", strip=True) if author_el else None
    if author and author.lower().startswith("by "):
        author = author[3:].strip()


    pub_date = pub_time = None
    published_el = soup.find("meta", attrs={"name": "article:published_time"})
    if published_el and published_el.get("content"):
        pub_date, pub_time = _split_datetime(published_el["content"])


    article_body = soup.find(attrs={"data-testid": "ArticleBody"})
    first_p_el = (
        article_body.find(attrs={"data-testid": "paragraph-0"}) if article_body else None
    )
    first_paragraph = first_p_el.get_text(" ", strip=True) if first_p_el else None

    return {
        "article_headline": headline,
        "publication_date": pub_date,
        "publication_time": pub_time,
        "author_name": author,
        "first_paragraph": first_paragraph,
    }


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
        result["extracted_data"] = scrape_reuters_html(file_path)
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
            "site": "reuters",
        },
    }


def main():
    parser = argparse.ArgumentParser(description="Reuters HTML scraper (BeautifulSoup)")
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
