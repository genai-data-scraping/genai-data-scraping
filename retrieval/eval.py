#!/usr/bin/env python3


import argparse
import json
import os
import sys
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

project_root = Path(__file__).resolve().parent
repo_root = project_root.parent
sys.path.insert(0, str(repo_root))
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv

load_dotenv(repo_root / ".env")

from launcher.project_tmp import ensure_tmp_dir
from config import settings
from scripts.sample_eval_urls import sample_eval_urls
from services.ladder_service import run_domain, write_summary
from services.llm_service import fetch_llm_pricing
from utils.url_utils import load_urls

ensure_tmp_dir()

PRESETS = {
    "smoke": {"urls_per_domain": 5, "output": "results/eval-smoke"},
    "full": {"urls_per_domain": 100, "output": "results/eval"},
}


class _Tee:
    def __init__(self, log_path: Path):
        self._log = open(log_path, "w", encoding="utf-8")
        self._stdout = sys.stdout
        self._stderr = sys.stderr

    def write(self, data):
        self._stdout.write(data)
        self._log.write(data)

    def flush(self):
        self._stdout.flush()
        self._log.flush()

    def close(self):
        self._log.close()

    def fileno(self):
        return self._stdout.fileno()

    def isatty(self):
        return self._stdout.isatty()


@contextmanager
def domain_log(log_path: Path):
    log_path.parent.mkdir(parents=True, exist_ok=True)
    tee = _Tee(log_path)
    old_out, old_err = sys.stdout, sys.stderr
    sys.stdout = sys.stderr = tee
    try:
        print(f"=== Eval log started {datetime.now(timezone.utc).isoformat()} ===")
        print(f"=== Log file: {log_path} ===\n")
        yield
    finally:
        print(f"\n=== Eval log finished {datetime.now(timezone.utc).isoformat()} ===")
        sys.stdout = old_out
        sys.stderr = old_err
        tee.close()


def run_eval(out_dir: Path, urls_dir: Path) -> None:
    url_files = sorted(urls_dir.glob("*.txt"))
    if not url_files:
        print(f"Error: no .txt files in {urls_dir}")
        sys.exit(1)

    logs_dir = out_dir / "logs"
    out_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)
    settings.HTML_OUTPUT_DIR = str(out_dir / "html")
    os.makedirs(settings.HTML_OUTPUT_DIR, exist_ok=True)

    print(f"\n{'═' * 55}")
    print("  Retrieval ladder — eval")
    print(f"{'═' * 55}")
    print(f"  Domains   : {len(url_files)}")
    print(f"  Model     : {settings.LLM_MODEL}")
    print(f"  Mode      : {settings.DEFAULT_MODE}")
    print(f"  Output    : {out_dir}/")
    print(f"  Logs      : {logs_dir}/")
    print(f"{'═' * 55}\n")

    fetch_llm_pricing()

    all_results = []
    for url_file in url_files:
        domain_urls = load_urls(str(url_file))
        if not domain_urls:
            continue

        for domain, urls in sorted(domain_urls.items()):
            log_name = url_file.stem if len(domain_urls) == 1 else f"{url_file.stem}_{domain}"
            log_path = logs_dir / f"{log_name}.log"

            print(f"\n▶ {domain} ({len(urls)} URLs) → {log_path.name}")

            with domain_log(log_path):
                print(f"  Domain : {domain}")
                print(f"  URLs   : {len(urls)}")
                print(f"  Source : {url_file.name}\n")
                domain_results = run_domain(domain, urls)
                all_results.extend(domain_results)
                ok = sum(1 for r in domain_results if r["success"])
                print(f"\n  ✓ [{domain}] done — {ok}/{len(urls)} succeeded")

            print(f"  Log saved → {log_path}")

    raw_path = out_dir / "ladder_results.json"
    with open(raw_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2)

    saved = sum(1 for r in all_results if r.get("html_path"))
    print(f"\nRaw results → {raw_path}")
    print(f"HTML saved  → {settings.HTML_OUTPUT_DIR}/ ({saved} files)")
    write_summary(all_results, str(out_dir))


def main():
    parser = argparse.ArgumentParser(
        description="Run retrieval eval (sample URLs + ladder + summary + logs)",
    )
    parser.add_argument(
        "preset",
        nargs="?",
        choices=list(PRESETS),
        default="smoke",
        help="smoke = 5 URLs/domain, full = 100 URLs/domain (default: smoke)",
    )
    parser.add_argument(
        "--no-resample",
        action="store_true",
        help="Use existing eval_urls/ instead of re-sampling",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed when sampling (default: 42)",
    )
    args = parser.parse_args()

    if not settings.OPENROUTER_API_KEY:
        print("Error: OPENROUTER_API_KEY not set (export it or add to .env).")
        sys.exit(1)
    if not settings.SCRAPINGBEE_API_KEY:
        print("Error: SCRAPINGBEE_API_KEY not set (export it or add to .env).")
        sys.exit(1)

    preset = PRESETS[args.preset]
    urls_dir = project_root / "eval_urls"
    out_dir = project_root / preset["output"]

    if not args.no_resample:
        print(f"\nSampling {args.preset} set ({preset['urls_per_domain']} URLs per domain)...")
        sample_eval_urls(n=preset["urls_per_domain"], seed=args.seed, out_dir=urls_dir)
        print()

    run_eval(out_dir=out_dir, urls_dir=urls_dir)


if __name__ == "__main__":
    main()
