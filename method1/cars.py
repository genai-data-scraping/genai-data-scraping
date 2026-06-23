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

_MPG_DISCLAIMER = (
    "Based on EPA mileage ratings. Use for comparison purposes only. "
    "Actual mileage will vary depending on driving conditions, driving habits, "
    "vehicle maintenance, and other factors."
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


def _clean_basics_value(text: str) -> str:
    return text.replace(_MPG_DISCLAIMER, "").strip()


def _listing_price(soup: BeautifulSoup) -> str | None:
    title_section = soup.find("div", class_="title-section")
    if title_section:
        container = title_section.parent
        if container:
            price_el = container.find("span", attrs={"data-qa": "primary-price"})
            if price_el:
                return price_el.get_text(strip=True)

    main = soup.find("main") or soup
    for price_el in main.select("span[data-qa='primary-price']"):
        if price_el.find_parent(attrs={"data-qa": "similar-vehicles"}):
            continue
        text = price_el.get_text(strip=True)
        if text:
            return text
    return None


def _seller_location(soup: BeautifulSoup) -> str | None:
    name_el = soup.find("h3", class_=re.compile(r"seller-name"))
    address_el = soup.find("div", class_="dealer-address")
    parts = []
    if name_el:
        parts.append(name_el.get_text(" ", strip=True))
    if address_el:
        parts.append(address_el.get_text(" ", strip=True))
    return ", ".join(parts) if parts else None


def _vehicle_basics(soup: BeautifulSoup) -> list[str]:
    items: list[str] = []
    for dl in soup.select("dl.fancy-description-list"):
        if dl.find_parent(attrs={"data-qa": "similar-vehicles"}):
            continue
        for dt in dl.find_all("dt"):
            dd = dt.find_next_sibling("dd")
            if not dd:
                continue
            label = dt.get_text(" ", strip=True)
            value = _clean_basics_value(dd.get_text(" ", strip=True))
            if label and value:
                items.append(f"{label}: {value}")
        if items:
            break
    return items


def _feature_highlights(soup: BeautifulSoup) -> list[str]:
    items: list[str] = []
    section = soup.find("section", class_="features-section")
    if section:
        for li in section.select("ul.vehicle-features-list li"):
            text = li.get_text(" ", strip=True)
            if text:
                items.append(text)

    auto_list = soup.select_one(".auto-corrected-feature-list")
    if auto_list:
        for part in auto_list.get_text(" ", strip=True).split(","):
            text = part.strip()
            if text:
                items.append(text)
    return items


def _all_features(soup: BeautifulSoup) -> list[str]:
    return [
        el.get_text(" ", strip=True)
        for el in soup.select(".all-features-item")
        if el.get_text(strip=True)
    ]


def _merge_unique(*groups: list[str]) -> list[str]:
    seen: set[str] = set()
    merged: list[str] = []
    for group in groups:
        for item in group:
            if item not in seen:
                seen.add(item)
                merged.append(item)
    return merged


def scrape_cars_html(html_path: str) -> dict[str, Any]:
    with open(html_path, encoding="utf-8", errors="replace") as fh:
        soup = BeautifulSoup(fh.read(), "html.parser")

    title_el = soup.find("h1", class_="listing-title")
    vehicle_model = title_el.get_text(" ", strip=True) if title_el else None

    mileage_el = soup.find("p", class_="listing-mileage")
    mileage = mileage_el.get_text(" ", strip=True) if mileage_el else None

    listed_price = _listing_price(soup)
    seller_location = _seller_location(soup)

    basics = _vehicle_basics(soup)
    highlights = _feature_highlights(soup)
    all_features = _all_features(soup)
    features_and_specs = _merge_unique(basics, highlights, all_features)

    return {
        "vehicle_model": vehicle_model,
        "listed_price": listed_price,
        "seller_location": seller_location,
        "mileage": mileage,
        "vehicle_features_and_specifications": features_and_specs,
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
        result["extracted_data"] = scrape_cars_html(file_path)
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
            "site": "cars.com",
        },
    }


def main():
    parser = argparse.ArgumentParser(description="Cars.com listing scraper (BeautifulSoup)")
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
