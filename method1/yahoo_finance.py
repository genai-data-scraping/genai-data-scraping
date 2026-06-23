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


def _clean_text(text: str | None) -> str | None:
    if text is None:
        return None
    cleaned = re.sub(r"\s+", " ", text).strip()
    return cleaned or None


def _company_name(soup: BeautifulSoup) -> str | None:
    heading = soup.select_one("section h1")
    if heading:
        return _clean_text(heading.get_text(" ", strip=True))

    if soup.title:
        title = soup.title.get_text(" ", strip=True)
        match = re.match(r"^(.+?)\s*\([A-Z^][A-Z0-9.-]+\)\s*Stock Price", title)
        if match:
            company = match.group(1).strip()
            ticker_match = re.search(r"\(([A-Z^][A-Z0-9.-]+)\)", title)
            if ticker_match:
                return f"{company} ({ticker_match.group(1)})"
            return company
    return None


def _quote_section(soup: BeautifulSoup):
    return soup.select_one('[data-testid="quote-price"]') or soup.select_one(
        '[data-testid="price-statistic"]'
    )


def _statistics_section(soup: BeautifulSoup):
    return soup.select_one('[data-testid="quote-statistics"]')


def _streamer_value(section, field: str) -> str | None:
    if not section:
        return None
    streamer = section.select_one(f'fin-streamer[data-field="{field}"]')
    if not streamer:
        return None
    return _clean_text(streamer.get("value") or streamer.get_text(" ", strip=True))


def scrape_yahoo_finance_html(html_path: str) -> dict[str, Any]:
    with open(html_path, encoding="utf-8", errors="replace") as fh:
        soup = BeautifulSoup(fh.read(), "html.parser")

    quote_section = _quote_section(soup)
    stats_section = _statistics_section(soup)

    price_el = None
    if quote_section:
        price_el = quote_section.select_one('[data-testid="qsp-price"]')
    if not price_el:
        price_el = soup.select_one('[data-testid="qsp-price"]')

    change_el = None
    pct_el = None
    if quote_section:
        change_el = quote_section.select_one('[data-testid="qsp-price-change"]')
        pct_el = quote_section.select_one('[data-testid="qsp-price-change-percent"]')
    if not change_el:
        change_el = soup.select_one('[data-testid="qsp-price-change"]')
    if not pct_el:
        pct_el = soup.select_one('[data-testid="qsp-price-change-percent"]')

    return {
        "company_name": _company_name(soup),
        "current_stock_price": _clean_text(price_el.get_text(" ", strip=True)) if price_el else None,
        "price_change": _clean_text(change_el.get_text(" ", strip=True)) if change_el else None,
        "percentage_change": _clean_text(pct_el.get_text(" ", strip=True)) if pct_el else None,
        "market_capitalization": _streamer_value(stats_section, "marketCap"),
        "fifty_two_week_price_range": _streamer_value(stats_section, "fiftyTwoWeekRange"),
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
        result["extracted_data"] = scrape_yahoo_finance_html(file_path)
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
            "site": "yahoo.finance.com",
        },
    }


def main():
    parser = argparse.ArgumentParser(description="Yahoo Finance quote scraper (BeautifulSoup)")
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
