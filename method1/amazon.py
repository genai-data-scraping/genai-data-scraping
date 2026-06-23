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


def _parse_rating(title: str | None) -> float | None:
    if not title:
        return None
    match = re.search(r"([\d.]+)\s*out of\s*5", title, re.I)
    return float(match.group(1)) if match else None


def _parse_review_count(text: str | None) -> int | None:
    if not text:
        return None
    match = re.search(r"([\d,]+)", text.replace("\xa0", " "))
    if not match:
        return None
    try:
        return int(match.group(1).replace(",", ""))
    except ValueError:
        return None


def _parse_brand(byline_text: str | None) -> str | None:
    if not byline_text:
        return None
    text = byline_text.strip()
    if text.lower().startswith("brand:"):
        return text.split(":", 1)[1].strip()
    match = re.search(r"Visit the\s+(.+?)\s+Store", text, re.I)
    if match:
        name = match.group(1).strip()
        if name.lower().endswith(" tablets"):
            return "Amazon"
        return name
    return text or None


def _price_from_block(block) -> str | None:
    offscreen = block.select_one(".a-offscreen")
    if offscreen:
        text = offscreen.get_text(strip=True)
        if text:
            return text
    whole = block.select_one(".a-price-whole")
    frac = block.select_one(".a-price-fraction")
    sym = block.select_one(".a-price-symbol")
    if whole and frac:
        symbol = sym.get_text(strip=True) if sym else "$"
        return f"{symbol}{whole.get_text(strip=True)}{frac.get_text(strip=True)}"
    return None


def _extract_prices(soup: BeautifulSoup) -> tuple[str | None, str | None]:

    current_prices: list[str] = []
    list_prices: list[str] = []

    search_roots = []
    core = soup.find(id="corePrice_desktop")
    if core:
        search_roots.append(core)
    buybox = soup.find(id="buybox")
    if buybox:
        search_roots.append(buybox)

    for root in search_roots:
        for block in root.select(
            ".priceToPay .a-price, .reinventPricePriceToPayMargin .a-price"
        ):
            price = _price_from_block(block)
            if price:
                current_prices.append(price)

        if not current_prices and root.get("id") == "buybox":
            for block in root.select(".a-price"):
                price = _price_from_block(block)
                if price and re.search(r"\$\d", price):
                    current_prices.append(price)
                    break

        for block in root.select(".basisPrice .a-price, .a-text-price .a-price"):
            price = _price_from_block(block)
            if price:
                list_prices.append(price)

        if current_prices:
            break

    if not current_prices:
        container = soup.find(id="tp-inline-twister-dim-values-container")
        if container:
            seen = set()
            for match in re.finditer(
                r"(\d+\s*GB[^$]*?(\$[\d,.]+)|Without Lockscreen Ads[^$]*?(\$[\d,.]+))",
                container.get_text(" ", strip=True),
                re.I,
            ):
                chunk = match.group(0).strip()
                if chunk not in seen:
                    seen.add(chunk)
                    current_prices.append(chunk)

    if not current_prices:
        for el in soup.select(".inline-twister-swatch-price .olpWrapper"):
            text = el.get_text(" ", strip=True).strip(".")
            if text:
                current_prices.append(text)

    current = " | ".join(dict.fromkeys(current_prices)) if current_prices else None
    list_price = list_prices[0] if list_prices else None
    return current, list_price


def _extract_features_and_specs(soup: BeautifulSoup) -> list[str]:
    items: list[str] = []
    seen: set[str] = set()

    def add(text: str | None) -> None:
        if not text:
            return
        cleaned = re.sub(r"\s+", " ", text).strip()
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            items.append(cleaned)

    bullets = soup.find(id="feature-bullets")
    if bullets:
        for li in bullets.select("li span.a-list-item"):
            add(li.get_text(" ", strip=True))

    for row in soup.select(
        "#productDetails_techSpec_section_1 tr, "
        "#productDetails_detailBullets_sections1 tr, "
        "table.prodDetTable tr"
    ):
        header = row.find("th")
        cell = row.find("td")
        if header and cell:
            add(f"{header.get_text(' ', strip=True)}: {cell.get_text(' ', strip=True)}")

    detail_bullets = soup.find(id="detailBullets_feature_div")
    if detail_bullets:
        for li in detail_bullets.select("li"):
            add(li.get_text(" ", strip=True))

    prod_details = soup.find(id="prodDetails")
    if prod_details:
        for row in prod_details.select("tr"):
            header = row.find("th")
            cell = row.find("td")
            if header and cell:
                add(f"{header.get_text(' ', strip=True)}: {cell.get_text(' ', strip=True)}")

    return items


def scrape_amazon_html(html_path: str) -> dict[str, Any]:
    with open(html_path, encoding="utf-8", errors="replace") as fh:
        soup = BeautifulSoup(fh.read(), "html.parser")

    title_el = soup.find(id="productTitle")
    product_name = title_el.get_text(" ", strip=True) if title_el else None

    byline_el = soup.find(id="bylineInfo")
    brand = _parse_brand(byline_el.get_text(" ", strip=True) if byline_el else None)

    rating_el = soup.find(id="acrPopover")
    average_rating = _parse_rating(rating_el.get("title") if rating_el else None)

    reviews_el = soup.find(id="acrCustomerReviewText")
    number_of_reviews = _parse_review_count(
        reviews_el.get_text(" ", strip=True) if reviews_el else None
    )

    price, list_price = _extract_prices(soup)
    features = _extract_features_and_specs(soup)

    return {
        "product_name": product_name,
        "price": price,
        "list_price": list_price,
        "brand": brand,
        "number_of_reviews": number_of_reviews,
        "average_rating": average_rating,
        "product_features_and_specifications": features,
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
        result["extracted_data"] = scrape_amazon_html(file_path)
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
            "site": "amazon",
        },
    }


def main():
    parser = argparse.ArgumentParser(description="Amazon product-page scraper (BeautifulSoup)")
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
