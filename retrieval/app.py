#!/usr/bin/env python3


import json
import os
import sys
import threading
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from dotenv import load_dotenv

project_root = Path(__file__).resolve().parent
repo_root = project_root.parent
sys.path.insert(0, str(repo_root))
sys.path.insert(0, str(project_root))

load_dotenv()

from launcher.project_tmp import ensure_tmp_dir
from config import settings
from services.ladder_service import run_domain, write_summary
from services.llm_service import fetch_llm_pricing
from utils.logging_utils import tprint
from utils.url_utils import load_urls

ensure_tmp_dir()


def main():
    parser = argparse.ArgumentParser(description="GenAI Scraping — Retrieval Ladder")
    parser.add_argument("urls_file", help="Text file with one URL per line")
    parser.add_argument("--output", default="results", help="Output directory")
    parser.add_argument(
        "--html-dir",
        default=None,
        help="Directory to save retrieved HTML (default: <output>/html)",
    )
    parser.add_argument(
        "--mode",
        choices=["ladder", "llm", "agent"],
        default="ladder",
        help="Retrieval strategy: ladder (ordered L1→L4), llm (pick level), "
             "agent (pick code level or ScrapingBee tool)",
    )
    args = parser.parse_args()

    settings.DEFAULT_MODE = args.mode

    if not settings.OPENROUTER_API_KEY:
        print("Error: OPENROUTER_API_KEY environment variable not set.")
        sys.exit(1)
    if not settings.SCRAPINGBEE_API_KEY:
        print("Error: SCRAPINGBEE_API_KEY environment variable not set.")
        sys.exit(1)

    fetch_llm_pricing()
    os.makedirs(args.output, exist_ok=True)

    settings.HTML_OUTPUT_DIR = args.html_dir or os.path.join(args.output, "html")
    os.makedirs(settings.HTML_OUTPUT_DIR, exist_ok=True)

    domain_urls = load_urls(args.urls_file)
    if not domain_urls:
        print("No URLs found in file.")
        sys.exit(1)

    total = sum(len(v) for v in domain_urls.values())
    print(f"\n{'═' * 55}")
    print("  GenAI Scraping — Retrieval Ladder")
    print(f"{'═' * 55}")
    print(f"  Domains  : {', '.join(sorted(domain_urls.keys()))}")
    print(f"  URLs     : {total}")
    print(f"  Model    : {settings.LLM_MODEL}")
    print(f"  Mode     : {settings.DEFAULT_MODE}")
    print(f"  Output   : {args.output}/")
    print(f"  HTML dir : {settings.HTML_OUTPUT_DIR}/")
    print(f"{'═' * 55}\n")

    all_results = []
    results_lock = threading.Lock()

    with ThreadPoolExecutor(max_workers=len(domain_urls)) as ex:
        futures = {
            ex.submit(run_domain, domain, urls): domain
            for domain, urls in domain_urls.items()
        }
        for fut in as_completed(futures):
            domain = futures[fut]
            try:
                domain_results = fut.result()
                with results_lock:
                    all_results.extend(domain_results)
                tprint(f"\n  ✓ [{domain}] done ({len(domain_results)} URLs)")
            except Exception as e:
                tprint(f"\n  ✗ [{domain}] crashed: {e}")

    raw_path = os.path.join(args.output, "ladder_results.json")
    with open(raw_path, "w") as f:
        json.dump(all_results, f, indent=2)
    print(f"\nRaw results → {raw_path}")

    saved = sum(1 for r in all_results if r.get("html_path"))
    print(f"Retrieved HTML files saved: {saved} → {settings.HTML_OUTPUT_DIR}/")
    write_summary(all_results, args.output)


if __name__ == "__main__":
    main()
