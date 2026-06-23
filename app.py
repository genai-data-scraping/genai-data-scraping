#!/usr/bin/env python3

import os
import re
import sys
import json
import shutil
import tempfile
import subprocess
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed

from dotenv import load_dotenv

from launcher.project_tmp import TMP_DIR, ensure_tmp_dir
from launcher.sample_data_service import (
    find_html_for_url,
    prepare_html_workspace,
    prepare_sample_workspace,
    site_folder_for_url,
)

load_dotenv()
ensure_tmp_dir()

ROOT = Path(__file__).resolve().parent
RETRIEVAL_DIR = ROOT / "retrieval"
if str(RETRIEVAL_DIR) not in sys.path:
    sys.path.insert(0, str(RETRIEVAL_DIR))

RESULTS_DIR = ROOT / "results"
SAMPLE_DATA_DIR = ROOT / "sample_data"
EXTRACTION_DIR = RESULTS_DIR / "extractions"
SCREENSHOT_DIR = RESULTS_DIR / "screenshots"
HTML_DIR = RESULTS_DIR / "html"
LOG_DIR = RESULTS_DIR / "logs"

SCRAPER_SCRIPTS = {
    "amazon": "amazon.py",
    "cars.com": "cars.py",
    "reuters": "reuters.py",
    "upwork": "upwork.py",
    "wikipedia": "wikipedia.py",
    "yahoo.finance": "yahoo_finance.py",
}


def scraper_script_for_directory(directory):
    dir_path = Path(directory)
    name = dir_path.name.lower()
    if "amazon" in name:
        return SCRAPER_SCRIPTS["amazon"]
    if "cars.com" in name or name == "cars":
        return SCRAPER_SCRIPTS["cars.com"]
    if "reuters" in name:
        return SCRAPER_SCRIPTS["reuters"]
    if "upwork" in name:
        return SCRAPER_SCRIPTS["upwork"]
    if "wikipedia" in name:
        return SCRAPER_SCRIPTS["wikipedia"]
    if "yahoo" in name or "finance" in name:
        return SCRAPER_SCRIPTS["yahoo.finance"]
    for html_path in dir_path.glob("*.html"):
        host = urlparse(extract_url_from_html(str(html_path))).netloc.lower()
        if "amazon" in host:
            return SCRAPER_SCRIPTS["amazon"]
        if "cars.com" in host:
            return SCRAPER_SCRIPTS["cars.com"]
        if "reuters" in host:
            return SCRAPER_SCRIPTS["reuters"]
        if "upwork.com" in host:
            return SCRAPER_SCRIPTS["upwork"]
        if "wikipedia.org" in host:
            return SCRAPER_SCRIPTS["wikipedia"]
        if "finance.yahoo.com" in host:
            return SCRAPER_SCRIPTS["yahoo.finance"]
    return SCRAPER_SCRIPTS["reuters"]


def extract_url_from_html(file_path):
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


METHODS = {
    "scraper": {
        "label": "Traditional scraper — site-specific rules, no LLM (method1)",
        "dir": ROOT / "method1",
        "workers": 5,
        "uses_prompt": False,
    },
    "html": {
        "label": "HTML — clean the page and extract with an LLM (method2)",
        "dir": ROOT / "method2",
        "workers": 5,
        "uses_prompt": True,
    },
    "screenshot": {
        "label": "Screenshot — open saved HTML from sample_data in Chrome and extract with a vision LLM (method3)",
        "dir": ROOT / "method3",
        "workers": None,
        "uses_prompt": True,
    },
    "websearch": {
        "label": "Web search — recover the URL and extract with a web-search LLM (websearch)",
        "dir": ROOT / "websearch",
        "script": "websearch_extractor.py",
        "workers": 2,
        "uses_prompt": True,
    },
}

SITE_PROMPTS = {
    "amazon.": (
        "Extract the following fields from this Amazon product page:\n"
        "- Product name\n"
        "- Price (identify any discount and the original/list price if shown)\n"
        "- Brand\n"
        "- Number of reviews and average rating\n"
        "- Product features and specifications\n"
        "Return the values you find; use null for anything not present."
    ),
    "cars.com": (
        "Extract the following fields from this Cars.com vehicle listing:\n"
        "- Vehicle model\n"
        "- Listed price\n"
        "- Seller location\n"
        "- Mileage\n"
        "- Vehicle features and specifications\n"
        "Return the values you find; use null for anything not present."
    ),
    "upwork.": (
        "Extract the following fields from this Upwork freelancer profile:\n"
        "- Freelancer name\n"
        "- Hourly rate\n"
        "- Full profile description\n"
        "- Number of jobs completed\n"
        "- Total number of hours worked\n"
        "Return the values you find; use null for anything not present."
    ),
    "reuters.": (
        "Extract the following fields from this Reuters article:\n"
        "- Article headline\n"
        "- Publication date\n"
        "- Publication time\n"
        "- Author name(s)\n"
        "- First paragraph of the article\n"
        "Return the values you find; use null for anything not present."
    ),
    "wikipedia.": (
        "Extract the following fields from this Wikipedia article:\n"
        "- Article title\n"
        "- First paragraph of the article\n"
        "- Key facts from the infobox (where present)\n"
        "- Table of contents\n"
        "- Last edited date\n"
        "Return the values you find; use null for anything not present."
    ),
    "finance.yahoo.": (
        "Extract the following fields from this Yahoo Finance quote page:\n"
        "- Company name\n"
        "- Current stock price\n"
        "- Price change and percentage change (vs the previous trading day's close)\n"
        "- Market capitalization\n"
        "- 52-week price range\n"
        "Return the values you find; use null for anything not present."
    ),
}


def _needs_openrouter(method_keys):
    return any(METHODS[m].get("uses_prompt", True) for m in method_keys)


def _require_openrouter(method_keys):
    if _needs_openrouter(method_keys) and not os.getenv("OPENROUTER_API_KEY"):
        print("Error: OPENROUTER_API_KEY environment variable not set.")
        print("  export OPENROUTER_API_KEY=...")
        print("  (Not required when running the scraper method alone.)")
        return False
    return True


def prompt_for_url(url):
    host = urlparse(url).netloc.lower()
    for key, prompt in SITE_PROMPTS.items():
        if key in host:
            return prompt
    return None


def hr(char="─", width=70):
    print(char * width)


def ask(prompt_text, default=None):
    suffix = f" [{default}]" if default is not None else ""
    while True:
        value = input(f"{prompt_text}{suffix}: ").strip()
        if value:
            return value
        if default is not None:
            return str(default)


def ask_int(prompt_text, default):
    while True:
        raw = ask(prompt_text, default)
        try:
            n = int(raw)
            if n <= 0:
                print("  Please enter a positive number.")
                continue
            return n
        except ValueError:
            print("  Please enter a whole number.")


def choose(prompt_text, options):
    print(f"\n{prompt_text}")
    keys = list(options)
    for i, (key, label) in enumerate(options, 1):
        print(f"  {i}) {label}")
    while True:
        raw = ask("Enter a number")
        try:
            idx = int(raw)
            if 1 <= idx <= len(keys):
                return keys[idx - 1][0]
        except ValueError:
            pass
        print(f"  Please enter a number between 1 and {len(keys)}.")


def choose_methods():
    keys = list(METHODS.keys())
    print("\nChoose one or more extraction methods "
          "(comma-separated, e.g. 1,3 — or 'all'). Multiple run in parallel:")
    for i, (k, v) in enumerate(METHODS.items(), 1):
        print(f"  {i}) {v['label']}")
    while True:
        raw = ask("Enter number(s)").lower()
        if raw in ("all", "*"):
            return keys
        try:
            chosen = []
            for token in re.split(r"[,\s]+", raw):
                if not token:
                    continue
                idx = int(token)
                if not (1 <= idx <= len(keys)):
                    raise ValueError
                key = keys[idx - 1]
                if key not in chosen:
                    chosen.append(key)
            if chosen:
                return chosen
        except ValueError:
            pass
        print(f"  Please enter number(s) between 1 and {len(keys)}, "
              "e.g. 1,3 or 'all'.")


def choose_retrieval_mode():
    return choose(
        "How should the retrieval agent choose which level to try?",
        [
            ("ladder", "Ordered ladder — climb L1→L2→L3→L4 in strict order on failure "
                       "(most predictable; L4 uses native ScrapingBee tool)"),
            ("llm", "LLM selector — the model picks the best untried level each round "
                    "(skips wasted attempts on easy sites)"),
            ("agent", "Agent + tools — the model chooses each step: generate code at "
                      "L1/L2/L3 OR invoke the ScrapingBee tool directly"),
        ],
    )


def ask_urls():
    print("\nPaste one or more URLs to retrieve (one per line, or separated by")
    print("  spaces/commas), then finish with an empty line. Processed in order.")
    lines = []
    while True:
        try:
            line = input()
        except EOFError:
            break
        if line.strip() == "":
            if lines:
                break
            continue
        lines.append(line)

    urls = []
    for line in lines:
        for token in re.split(r"[\s,]+", line.strip()):
            if not token:
                continue
            if not token.startswith(("http://", "https://")):
                token = "https://" + token
            if token not in urls:
                urls.append(token)
    return urls


def ask_prompt_text():
    print("\nWhat should the model extract from the page?")
    print("  Type or paste your instructions, then finish with an empty line.")
    print("  (Press Enter on an empty line right away to use the method's default prompt.)")
    lines = []
    while True:
        try:
            line = input()
        except EOFError:
            break
        if line.strip() == "":
            break
        lines.append(line)
    return "\n".join(lines).strip()


def run_extraction_method(method_key, directory=None, num_files=None,
                          prompt_text=None, log_file=None):
    method = METHODS[method_key]
    EXTRACTION_DIR.mkdir(parents=True, exist_ok=True)

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    output_path = EXTRACTION_DIR / f"{method_key}_{stamp}.json"

    script = method.get("script", "app.py")
    if method_key == "scraper":
        script = scraper_script_for_directory(directory)
    cmd = [sys.executable, script, "-o", str(output_path)]
    cmd += ["-d", str(Path(directory).resolve()), "-n", str(num_files)]
    if method["workers"] is not None:
        cmd += ["-w", str(min(method["workers"], num_files))]
    if method_key == "screenshot":
        cmd += ["--screenshot-dir", str(SCREENSHOT_DIR.resolve()), "--preview"]

    prompt_file = None
    if prompt_text and method.get("uses_prompt", True):
        fd, prompt_file = tempfile.mkstemp(prefix="prompt_", suffix=".txt", dir=str(TMP_DIR))
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(prompt_text)
        cmd += ["-p", str(Path(prompt_file).resolve())]

    if log_file is None:
        print()
        hr("═")
        print(f"  Running '{method_key}' extraction → {output_path.name}")
        if method_key == "scraper":
            print(f"  Using traditional site-specific scraper ({script}, no LLM).")
        elif prompt_file:
            print("  Using your custom prompt.")
        else:
            print(f"  Using {method_key}'s default prompt.txt.")
        hr("═")

    try:
        if log_file is not None:
            with open(log_file, "w", encoding="utf-8") as lf:
                proc = subprocess.run(cmd, cwd=str(method["dir"]),
                                      stdout=lf, stderr=subprocess.STDOUT)
        else:
            proc = subprocess.run(cmd, cwd=str(method["dir"]))
    finally:
        if prompt_file:
            try:
                os.unlink(prompt_file)
            except OSError:
                pass

    if log_file is None:
        if proc.returncode != 0:
            print(f"\n  ✗ '{method_key}' extraction exited with code {proc.returncode}.")
            _print_failure_hint(method_key, log_file=log_file)
        _summarize_output(output_path)
    return output_path, proc.returncode


def _last_log_error(log_file):
    if not log_file:
        return None
    path = Path(log_file)
    if not path.exists():
        return None
    last = None
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if " - ERROR - " in line:
            last = line.split(" - ERROR - ", 1)[-1].strip()
    return last


def _print_failure_hint(method_key, log_file=None):
    err = _last_log_error(log_file)
    if err:
        print(f"    Error: {err[:300]}")
        return
    if method_key == "screenshot":
        print("    (Screenshotting HTML needs a local Chrome install.)")


def run_jobs(jobs, prompt_text=None):
    if not jobs:
        print("\n  Nothing to extract.")
        return

    if len(jobs) == 1:
        j = jobs[0]
        run_extraction_method(j["method_key"], directory=j.get("directory"),
                              num_files=j.get("num_files"), prompt_text=prompt_text)
        return

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    names = ", ".join(j["method_key"] for j in jobs)

    print()
    hr("═")
    print(f"  Running {len(jobs)} methods in parallel: {names}")
    print("  Live output is captured per method; summaries follow below.")
    hr("═")

    def work(j):
        log_file = LOG_DIR / f"{j['method_key']}_{stamp}.log"
        print(f"  ▶ {j['method_key']} started  (log → {log_file.relative_to(ROOT)})")
        output_path, rc = run_extraction_method(
            j["method_key"], directory=j.get("directory"),
            num_files=j.get("num_files"), prompt_text=prompt_text,
            log_file=str(log_file))
        print(f"  {'✓' if rc == 0 else '✗'} {j['method_key']} finished (exit {rc})")
        return j["method_key"], output_path, rc, log_file

    results = {}
    with ThreadPoolExecutor(max_workers=len(jobs)) as pool:
        futures = [pool.submit(work, j) for j in jobs]
        for fut in as_completed(futures):
            key, output_path, rc, log_file = fut.result()
            results[key] = (output_path, rc, log_file)

    print()
    hr("═")
    print("  Combined results")
    hr("═")
    for j in jobs:
        key = j["method_key"]
        output_path, rc, log_file = results[key]
        print(f"\n  [{key}]  exit {rc}   (log → {log_file.relative_to(ROOT)})")
        if rc != 0:
            _print_failure_hint(key, log_file=log_file)
        _summarize_output(output_path)


def _summarize_output(output_path):
    if not output_path.exists():
        print(f"  (No output file written at {output_path})")
        return
    try:
        data = json.loads(output_path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"  Could not read output JSON: {e}")
        return

    summary = data.get("summary")
    if isinstance(summary, dict):
        print("\n  Result summary:")
        for k in ("total_requested", "total_processed", "successful", "failed", "site"):
            if k in summary:
                print(f"    {k:<16}: {summary[k]}")
        for k in ("total_llm_processing_time_seconds", "avg_llm_processing_time_seconds"):
            if k in summary:
                print(f"    {k:<16}: {summary[k]}s")

    processing_info = data.get("processing_info")
    if isinstance(processing_info, dict):
        llm_total = processing_info.get("total_llm_processing_time_seconds")
        if llm_total is not None:
            print(f"    total_llm_processing_time_seconds: {llm_total}s")

    files = data.get("processed_files", [])
    llm_times = [
        f.get("llm_processing_time_seconds")
        for f in files
        if f.get("llm_processing_time_seconds") is not None
    ]
    if llm_times and not (
        isinstance(summary, dict) and "total_llm_processing_time_seconds" in summary
    ):
        print(f"    total_llm_processing_time_seconds: {round(sum(llm_times), 3)}s")

    print(f"\n  Full results → {output_path}")


def domain_for(url):
    host = urlparse(url).netloc.replace("www.", "")
    return ".".join(host.split(".")[-2:]) or "site"


def find_cached_html(url):
    from services.storage_service import safe_filename

    candidate = HTML_DIR / domain_for(url) / safe_filename(url)
    return candidate if candidate.exists() else None


def _retrieve_and_extract_one(url, method_keys, prompt_text):
    from services.ladder_service import run_ladder

    work_dirs = []
    html_work_dir = None
    html_ok = False
    needs_retrieval = any(m in ("html", "websearch", "scraper") for m in method_keys)

    if needs_retrieval:
        cached = find_cached_html(url)
        if cached is not None:
            html_ok = True
            print(f"\n  ✓ Using cached HTML (skipping retrieval): "
                  f"{cached.relative_to(ROOT)}")
            html_work_dir = tempfile.mkdtemp(prefix="retrieved_", dir=str(TMP_DIR))
            work_dirs.append(html_work_dir)
            shutil.copy(cached, os.path.join(html_work_dir, cached.name))
        else:
            domain = domain_for(url)
            print()
            hr("─")
            print(f"  Retrieval agent starting for: {url}")
            hr("─")

            result = run_ladder(url, domain)
            if result.get("success"):
                html_ok = True
                print(f"\n  ✓ Retrieved at {result.get('level_label')} "
                      f"({result.get('html_chars'):,} chars).")
                html_work_dir = tempfile.mkdtemp(prefix="retrieved_", dir=str(TMP_DIR))
                work_dirs.append(html_work_dir)
                html_path = result.get("html_path")
                shutil.copy(html_path, os.path.join(html_work_dir, os.path.basename(html_path)))
            else:
                print("\n  ✗ Retrieval failed at all levels — "
                      "HTML/scraper/web-search methods can't run for this URL.")

    jobs = []
    for m in method_keys:
        if m in ("html", "websearch", "scraper"):
            if html_ok:
                jobs.append({"method_key": m, "directory": html_work_dir, "num_files": 1})
            elif m == "scraper":
                sample_html = find_html_for_url(url, SAMPLE_DATA_DIR)
                if sample_html is None:
                    site = site_folder_for_url(url, SAMPLE_DATA_DIR)
                    hint = (f" (no saved page for this URL under "
                            f"{site.relative_to(ROOT) if site else SAMPLE_DATA_DIR.relative_to(ROOT)})")
                    print(f"\n  ✗ Skipping scraper: no HTML available{hint}")
                    continue
                sample_work_dir = prepare_html_workspace(sample_html)
                work_dirs.append(sample_work_dir)
                print(f"\n  ✓ Scraper will use sample_data: "
                      f"{sample_html.relative_to(ROOT)}")
                jobs.append({
                    "method_key": "scraper",
                    "directory": sample_work_dir,
                    "num_files": 1,
                })
        elif m == "screenshot":
            sample_html = find_html_for_url(url, SAMPLE_DATA_DIR)
            if sample_html is None:
                site = site_folder_for_url(url, SAMPLE_DATA_DIR)
                hint = (f" (no saved page for this URL under "
                        f"{site.relative_to(ROOT) if site else SAMPLE_DATA_DIR.relative_to(ROOT)})")
                print(f"\n  ✗ Skipping screenshot: no matching HTML in sample_data{hint}")
                continue
            sample_work_dir = prepare_html_workspace(sample_html)
            work_dirs.append(sample_work_dir)
            print(f"\n  ✓ Screenshot will use sample_data: "
                  f"{sample_html.relative_to(ROOT)}")
            jobs.append({
                "method_key": "screenshot",
                "directory": sample_work_dir,
                "num_files": 1,
            })

    try:
        run_jobs(jobs, prompt_text=prompt_text)
    finally:
        for wd in work_dirs:
            shutil.rmtree(wd, ignore_errors=True)


def mode_retrieve_url():
    urls = ask_urls()
    if not urls:
        print("  No URLs given.")
        return
    method_keys = choose_methods()
    if not _require_openrouter(method_keys):
        return

    prompts = {}
    for url in urls:
        site_prompt = prompt_for_url(url)
        if site_prompt is None:
            print(f"\nUnrecognised site for: {url}")
            prompts[url] = ask_prompt_text()
        else:
            host = urlparse(url).netloc
            print(f"\nUsing the built-in prompt for {host}:")
            print("  " + site_prompt.splitlines()[0])
            prompts[url] = site_prompt

    if any(m in ("html", "websearch", "scraper") for m in method_keys):
        from config import settings as retrieval_settings
        from services.llm_service import fetch_llm_pricing

        retrieval_settings.HTML_OUTPUT_DIR = str(HTML_DIR)
        HTML_DIR.mkdir(parents=True, exist_ok=True)
        cached_count = sum(find_cached_html(u) is not None for u in urls)
        if cached_count:
            print(f"\n  {cached_count}/{len(urls)} URL(s) already retrieved — "
                  "those will reuse cached HTML.")
        if cached_count < len(urls):
            retrieval_settings.DEFAULT_MODE = choose_retrieval_mode()
            try:
                fetch_llm_pricing()
            except Exception:
                pass

    total = len(urls)
    for i, url in enumerate(urls, 1):
        print()
        hr("═")
        print(f"  URL {i}/{total}: {url}")
        hr("═")
        _retrieve_and_extract_one(url, method_keys, prompts[url])

    print(f"\n  Finished {total} URL(s).")


def _folders_with_html(base):
    base = Path(base)
    if not base.exists():
        return []
    found = []
    if list(base.glob("*.html")):
        found.append(base)
    for sub in sorted(p for p in base.iterdir() if p.is_dir()):
        if list(sub.glob("*.html")):
            found.append(sub)
    return found


def mode_existing_files():
    method_keys = choose_methods()
    if not _require_openrouter(method_keys):
        return

    candidates = []
    if SAMPLE_DATA_DIR.is_dir():
        candidates.extend(_folders_with_html(SAMPLE_DATA_DIR))
    candidates.extend(_folders_with_html(HTML_DIR))

    if candidates:
        options = [(str(p), f"{p.relative_to(ROOT)}  ({len(list(p.glob('*.html')))} files)")
                   for p in candidates]
        options.append(("__custom__", "Enter a different folder path"))
        chosen = choose("Choose a folder of HTML files:", options)
        directory = ask("Folder path") if chosen == "__custom__" else chosen
    else:
        print(f"\nNo HTML files found under {SAMPLE_DATA_DIR.relative_to(ROOT)} "
              f"or {HTML_DIR.relative_to(ROOT)}.")
        directory = ask("Enter a folder containing .html files")

    if not Path(directory).exists():
        print(f"  ✗ Folder not found: {directory}")
        return

    num_files = ask_int("How many random samples to run", default=3)
    prompt_text = ask_prompt_text() if _needs_openrouter(method_keys) else None

    try:
        sample_dir, selected = prepare_sample_workspace(directory, num_files)
    except FileNotFoundError as e:
        print(f"  ✗ {e}")
        return

    print(f"\n  Using the same {len(selected)} sample(s) for all methods:")
    for path in selected:
        print(f"    • {Path(path).name}")

    jobs = [
        {"method_key": m, "directory": sample_dir, "num_files": len(selected)}
        for m in method_keys
    ]
    try:
        run_jobs(jobs, prompt_text=prompt_text)
    finally:
        shutil.rmtree(sample_dir, ignore_errors=True)


def main():
    print()
    hr("═")
    print("  GenAI Scraping — Interactive Launcher")
    hr("═")

    mode = choose(
        "How do you want to run it?",
        [
            ("url", "Retrieve from URL(s) (runs the retrieval agent, then extracts)"),
            ("files", "Use existing HTML files (choose samples, then extracts)"),
        ],
    )

    if mode == "url":
        mode_retrieve_url()
    else:
        mode_existing_files()

    print("\nDone.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted.")
        sys.exit(1)
