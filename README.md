# Generative AI for Data Scraping

This is the codebase accompanying the paper [**Generative AI for Data Scraping**](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=5353923). The repo has two main parts:

1. **Retrieval** — an escalating L1→L4 ladder that fetches live page HTML using LLM-generated code and an LLM judge.
2. **Extraction** — four downstream methods that pull structured fields from saved HTML (or via screenshots / web search).

The interactive launcher (`app.py` at the repo root) runs retrieval + extraction together. For retrieval-only batch runs and paper-style evals, please use `retrieval/eval.py`.

---

## What this repo does

| Stage | What happens |
|-------|----------------|
| **Retrieval** | Fixed ladder L1→L4. At each level the LLM generates Python fetch code once; the runner executes it (with same retries on transient errors). An LLM judge accepts or rejects the HTML before escalating. |
| **Extraction** | Rules-based scraper, cleaned HTML + LLM, local screenshots + vision LLM, or web-search LLM. These can be run in parallel when selected. |

The paper compares extraction approaches across several real-world sites. This repository lets you reproduce those runs on bundled sample pages or on live URLs you provide.

> Please note results may vary slightly from the paper due to LLM stochasticity, but everything will hold directionally. Additionally, as observed during our implementation, LLM performance and repsonse time varies depending on the provider OpenRouter selects. This implementation includes some improvements to HTML cleaning and processing efficiency for the LLM extraction methods, which reduce API costs and processing time.

---

## Architecture

**Root launcher (`app.py`)** — interactive pipeline:

1. **Live URLs** — retrieval ladder fetches pages → HTML cached under `results/html/<domain>/` → extraction runs.
2. **Saved HTML** — skip retrieval; extract from `sample_data/` or cached `results/html/`.

**Retrieval (`retrieval/`)** — see [Retrieval ladder](#retrieval-ladder) below. All four levels use LLM-generated code (including L4 ScrapingBee). The LLM writes code; it never decides routing in ladder mode.

**Extraction** — parallel methods when selected:

| Method | Folder | Approach |
|--------|--------|----------|
| Scraper | `method1/` | BeautifulSoup + CSS selectors (6 sites) |
| HTML | `method2/` | Clean HTML → markdown → LLM |
| Screenshot | `method3/` | Selenium screenshots → vision LLM |
| Web search | `websearch/` | URL → web-search LLM |

**Outputs** — under `results/` (git-ignored): extraction JSON, logs, cached HTML, screenshots. Retrieval evals write to `retrieval/results/`.

Implementation details for the retrieval ladder: `retrieval/IMPLEMENTATION_SPEC.md`.

---

## Available data

Each saved page is a complete HTML file plus a matching `*_files/` asset folder. 

This repo contains a **small sample** in `sample_data/` (4–5 pages per site, except Upwork) for quick tests. **Full datasets** (1,000 pages per domain) are available via Google Drive (see below).

| Site | Pages | Typical page size | In `sample_data/` | Full HTML download |
|------|------:|-------------------|-------------------|--------------------|
| [amazon.com](https://www.amazon.com) | 1,000 | 1.6–2.6 MB | 4 sample pages | [Google Drive](https://drive.google.com/file/d/1byuQSdUctjHvNsjYrMcV-mZX1Phr2nTO/view?usp=drive_link) |
| [cars.com](https://www.cars.com) | 1,000 | 1.1–3.0 MB | 4 sample pages | [Google Drive](https://drive.google.com/file/d/1GooU4kLtwoq82Jp1SaxLEJqwcilDBpzF/view?usp=sharing) |
| [reuters.com](https://www.reuters.com) | 1,000 | 8.6–28.3 MB | 5 sample pages | [Google Drive](https://drive.google.com/file/d/1o3SQ-iAGg3hHdTGgcMPUjRzK3oebw_DF/view?usp=drive_link) |
| [wikipedia.org](https://www.wikipedia.org) | 1,000 | 0.8–4.2 MB | 5 sample pages | [Google Drive](https://drive.google.com/file/d/1IamL907IWv0iFKOEUm33GDBLzWqDbbwR/view?usp=drive_link) |
| [finance.yahoo.com](https://finance.yahoo.com) | 1,000 | 5.5–20.3 MB | 5 sample pages | [Google Drive](https://drive.google.com/file/d/1tLBAS0xw8Y_hRBUAd6g19gSNRrfE95-J/view?usp=drive_link) |
| [upwork.com](https://www.upwork.com) | 1,000 | 6.4–13.0 MB | — | **Not shared publicly** (contains personal profile data) |

### amazon.com

- **Format:** Complete HTML files with associated assets
- **Content:** Product pages (HTML + assets) — tablets, electronics, home goods, etc.
- **File size:** ~1.6–2.6 MB per page
- **Count:** 1,000 product pages

### cars.com

- **Format:** Complete HTML files with associated assets
- **Content:** Vehicle listings (HTML + assets) — sedans, SUVs, trucks, sports cars, etc.
- **File size:** ~1.1–3.0 MB per page
- **Count:** 1,000 vehicle listings

### reuters.com

- **Format:** Complete HTML files with associated assets
- **Content:** News articles (HTML + assets)
- **File size:** ~8.6–28.3 MB per page
- **Count:** 1,000 articles

### wikipedia.org

- **Format:** Complete HTML files with associated assets
- **Content:** City/town encyclopedia articles (HTML + assets)
- **File size:** ~0.8–4.2 MB per page
- **Count:** 1,000 articles

### finance.yahoo.com

- **Format:** Complete HTML files with associated assets
- **Content:** Stock quote pages (HTML + assets)
- **File size:** ~5.5–20.3 MB per page
- **Count:** 1,000 quote pages

### upwork.com

- **Format:** Complete HTML files with associated assets
- **Content:** Freelancer profiles (HTML + assets)
- **File size:** 6.4–13.0 MB per page
- **Count:** 1,000 freelancer profiles
- **Availability:** Not shared publicly, as profiles contain sensitive personal information. 

### URL lists (in this repo)

The URL lists (one URL per line) live in [`urls/`](urls/); these are useful for retrieval eval sampling and for re-downloading pages:

| File | URLs |
|------|-----:|
| `urls/amazon.com.txt` | 1,000 |
| `urls/cars.com.txt` | 1,000 |
| `urls/reuters.txt` | 1,000 |
| `urls/wikipedia.org.txt` | 1,000 |
| `urls/yahoo.finance.com.txt` | 1,000 |
| `urls/upwork.com.txt` | 1,000 |

After downloading a full dataset, point `app.py` mode 2 or the method CLIs at the unpacked folder (same layout as `sample_data/<site>/`).

---

## Prerequisites

- **Python 3.11+**
- **Google Chrome** — screenshot method (`method3`)
- **Playwright Chromium** — retrieval L3 and some HTML cleaning

```bash
playwright install chromium
```

**API keys** (`.env` at repo root or exported):

| Variable | Used for |
|----------|----------|
| `OPENROUTER_API_KEY` | Retrieval ladder (code gen + judge) and all LLM extraction methods |
| `SCRAPINGBEE_API_KEY` | Retrieval L4 (required for batch/eval runs that may reach L4) |

---

## Setup

```bash
git clone <this-repo>
cd scraping-revision-final

python3 -m venv venv
source venv/bin/activate

pip install -r requirements.txt
playwright install chromium
```

Create `.env`:

```bash
OPENROUTER_API_KEY=sk-or-...
SCRAPINGBEE_API_KEY=...
```

---

## Quick start

### Full pipeline (retrieval + extraction)

```bash
source venv/bin/activate
python app.py
```

Choose **Retrieve from URL(s)** or **Use existing HTML files**, then pick extraction method(s). Results go to `results/extractions/` and `results/logs/`.

### Retrieval eval only

```bash
cd retrieval
python eval.py          # smoke: 5 URLs × 5 domains
python eval.py full     # full:  100 URLs × 5 domains
```

Confirm at startup: `Pricing fetched for anthropic/claude-sonnet-4.6` (not a "not found" warning).

---

## Retrieval ladder

### How it works

1. **Fixed order** — L1 → L2 → L3 → L4 in `ladder` mode (default).
2. **One codegen per rung** — LLM generates fetch code once; transient failures retry the *same* script (no re-generation on 429/5xx).
3. **LLM judge** — replaces all byte thresholds and hardcoded bot checks. Reject → escalate with judge reason in feedback. Unparseable judge response → fail closed. Judge API unreachable → lean accept with `judge_unavailable=True` (reported separately in summary).
4. **Escalation** — deterministic failures (403, judge reject) move to the next level immediately. Transient failures (429, 5xx, timeout) retry within the rung budget first.

| Level | Label | Technique |
|-------|-------|-----------|
| L1 | Plain Requests | Simple `requests.get` |
| L2 | Requests + Headers | Realistic browser headers |
| L3 | Playwright Stealth | Headless Chromium + `playwright-stealth` |
| L4 | ScrapingBee | LLM-generated ScrapingBee API call (premium proxy + JS render) |

**Retry budgets:** L1–L3 = 3 attempts per rung; L4 = 5. Backoff with jitter between same-rung retries. `INTER_URL_DELAY_SECONDS` (default 2s) pauses between URLs within a domain.

**Retrieval modes** (`retrieval/config/settings.py`, overridable via CLI):

| Mode | Behaviour |
|------|-----------|
| `ladder` | Strict L1→L2→L3→L4. Default. |
| `llm` | Model picks the best untried level each round. |
| `agent` | Model picks which code level to generate next (including L4). |

**Model:** `anthropic/claude-sonnet-4.6` via OpenRouter (`retrieval/config/settings.py`).

### Key files

| File | Role |
|------|------|
| `retrieval/eval.py` | One-command eval (sample + run + summary + logs) |
| `retrieval/app.py` | Batch retrieval CLI (URL file → HTML) |
| `retrieval/services/ladder_service.py` | Escalation loop, summary table |
| `retrieval/services/execution_service.py` | Subprocess runner + judge call |
| `retrieval/services/judge_service.py` | LLM judge + resilience |
| `retrieval/services/llm_service.py` | Code generation, level selection |
| `retrieval/services/storage_service.py` | Save HTML |
| `retrieval/config/settings.py` | Prompts, retry budgets, model |

### Retrieval eval

Eval uses **five domains** (Upwork excluded): amazon, cars, reuters, wikipedia, yahoo.

URL lists are sampled randomly from `urls/` into `retrieval/eval_urls/` (seed 42 by default).

```bash
cd retrieval

# Smoke (~25 URLs total) — good first run
python eval.py

# Full eval (~500 URLs total)
python eval.py full

# Re-use existing samples without re-drawing
python eval.py full --no-resample
```

**Outputs** (`results/eval-smoke/` or `results/eval/`):

| Output | Description |
|--------|-------------|
| `ladder_summary.txt` | Summary table: Succ%, AvgLevel, cost, time, L1–L4 counts, **Unjd** (unjudged accepts) |
| `ladder_results.json` | Per-URL results with full attempt history |
| `logs/<domain>.log` | One log file per domain (5 files) |
| `html/<domain>/` | Saved HTML for successful fetches |

**Reading eval results:**

1. **AvgLevel** per domain — inflated on easy domains suggests false-rejects (needless escalation).
2. **Unjd** — nonzero means some successes were accepted without a judge verdict (soft success rate).
3. Spot-check **`judge_reject`** reasons in `ladder_results.json` history.
4. Spot-check **accepted HTML** on JS-heavy domains (amazon, reuters, yahoo) — false-accept shells do not appear in any column.

**Unit tests** (mechanism only, no live API calls):

```bash
cd retrieval
PYTHONPATH=..:. python -m pytest tests/ -q
```

### Batch retrieval (no eval wrapper)

```bash
cd retrieval
python app.py urls.txt --output results/ --mode ladder
```

One URL per line. Same ladder as eval; no per-domain log files or auto-sampling.

---

## The launcher in detail

### Mode 1 — Retrieve from URL(s)

1. Paste URLs (one per line), press Enter on empty line.
2. Choose extraction method(s).
3. Built-in site prompts for recognised hosts:

   | Host pattern | Fields extracted |
   |---|---|
   | `amazon.*` | Product name, price, brand, reviews/rating, features |
   | `cars.com` | Model, price, location, mileage, specs |
   | `upwork.*` | Name, hourly rate, description, jobs completed, hours |
   | `reuters.*` | Headline, date, time, author, first paragraph |
   | `wikipedia.*` | Title, lede, infobox facts, TOC, last edited |
   | `finance.yahoo.*` | Company, price, change, market cap, 52-week range |

4. Choose retrieval mode (`ladder` / `llm` / `agent`) if HTML methods need fresh pages.
5. Retrieved pages cached under `results/html/<domain>/`.

**Screenshot note:** in URL mode, screenshot extraction looks up a matching page in `sample_data/` — it does not render freshly retrieved HTML.

### Mode 2 — Use existing HTML files

Best for **replicating paper extraction evals** on bundled data.

1. Choose extraction method(s).
2. Pick a folder under `sample_data/` or `results/html/`.
3. Enter random sample count (e.g. `3`).
4. Accept default prompt or paste custom.

All selected methods process the **same random sample set** for direct comparison.

---

## Extraction methods

| Key | Folder | Model (OpenRouter) | Input | API key? |
|-----|--------|-------------------|-------|----------|
| `scraper` | `method1/` | — | Saved HTML | No |
| `html` | `method2/` | `meta-llama/llama-3.1-8b-instruct` | Cleaned HTML → markdown | Yes |
| `screenshot` | `method3/` | `mistralai/mistral-small-3.2-24b-instruct` | Selenium screenshots | Yes |
| `websearch` | `websearch/` | `openai/gpt-4o-search-preview-2025-03-11` | URL from HTML comment | Yes |

### `scraper` (method1)

Site-specific BeautifulSoup scrapers (saved HTML only). Returns structured JSON in `extracted_data`:

| Script | Site | Fields |
|--------|------|--------|
| `reuters.py` | Reuters | headline, date, time, author, first paragraph |
| `amazon.py` | Amazon | product name, price, list price, brand, reviews, rating, features/specs |
| `cars.py` | Cars.com | model, price, seller location, mileage, features/specs |
| `upwork.py` | Upwork | name, hourly rate, profile description, jobs completed, hours worked |
| `wikipedia.py` | Wikipedia | title, first paragraph, infobox facts, TOC, last edited date |
| `yahoo_finance.py` | Yahoo Finance | company name, price, change, % change, market cap, 52-week range |

`app.py` picks the script from the folder name or saved-page URL.

### `html` (method2)

Strips boilerplate, extracts JSON-LD/meta, converts to markdown (~80k char cap), sends to LLM.

### `screenshot` (method3)

Renders saved HTML locally in Chrome via Selenium; 4 viewport screenshots (1920×1080, 270px overlap) → vision LLM.

### `websearch` (websearch)  - the naive AI method

Reads the original URL from the saved-page comment; a web-search-enabled LLM re-fetches the live page and extracts fields.

**Expected reliability issues.** Provided your API key and environment are correctly configured, inconsistent and frequently failing results across runs are *expected behavior*, not a bug. This includes:

- “Unable to access the specific URL” errors
- Incomplete or missing extractions
- Different results for the same URL across runs

These are the reliability issues analyzed in Section 6 and Table 4 of the paper. An 18,000-run stability test found accuracy ranging from 0–100% on identical URLs. Such failures reflect the method itself and demonstrate its unsuitability for production use.

Entry point: `websearch/websearch_extractor.py`.
---

## Replicating extraction evaluation

### Reuters (primary benchmark)

```bash
python app.py
```

1. **Use existing HTML files**
2. Methods: **`all`**
3. Folder: **`sample_data/reuters`**
4. Samples: **`3`**
5. Prompt: Enter for defaults, or use the Reuters prompt from `app.py` `SITE_PROMPTS`.

Expected outputs: `results/extractions/<method>_<timestamp>.json` and `results/logs/<method>_<timestamp>.log`.

| Method | Typical overall |
|--------|----------------|
| Scraper | ~100% |
| HTML | ~95% |
| Screenshot | ~95% |
| Websearch | varies |

Scraper writes `extracted_data` (JSON). LLM methods write `llm_response` (free text).

### Other sites

Same workflow with `sample_data/amazon.com/`, `sample_data/cars.com/`, `sample_data/wikipedia.org/`, or `sample_data/yahoo.finance.com/` and matching prompts from `app.py`. For Upwork, use a local copy of the full dataset (not included in this repo).

---

## Running methods directly

```bash
# Scraper — no API key (examples)
cd method1 && python reuters.py -d ../sample_data/reuters -n 3 -o results.json
cd method1 && python amazon.py -d ../sample_data/amazon.com -n 3 -o results.json

# Upwork scraper — requires local HTML (not bundled; not shared publicly)
# cd method1 && python upwork.py -d /path/to/upwork.com -n 3 -o results.json

# HTML + LLM
cd method2 && python app.py -d ../sample_data/reuters -n 3 -p prompt.txt -o results.json

# Screenshot + vision LLM
cd method3 && python app.py -d ../sample_data/amazon.com -n 1 \
  --screenshot-dir ../results/screenshots -o results.json

# Web search (naive AI method)
cd websearch && python websearch_extractor.py -d ../sample_data/reuters -n 3 -o results.json
```

Flags: `-d` directory, `-n` random count, `-o` output JSON, `-p` prompt file, `-w` workers.

---

## Output locations

| Path | Contents |
|------|----------|
| `results/extractions/` | Extraction JSON (`scraper_`, `html_`, `screenshot_`, `websearch_` + timestamp) |
| `results/logs/` | Extraction method logs |
| `results/html/<domain>/` | Cached retrieved pages (launcher mode 1) |
| `results/screenshots/` | PNG captures from method3 |
| `results/tmp/` | Temp workspaces |
| `retrieval/results/eval-smoke/` | Smoke eval outputs |
| `retrieval/results/eval/` | Full eval outputs |

`results/` is git-ignored. Delete to start fresh.

---

## Evaluation methodology

Paper accuracy uses **strict field-by-field exact match**:

- Each field scored independently.
- First paragraph excludes dateline prefix and second-sentence spillover.
- LLM free-text responses cause parsing false negatives.
- Minor formatting differences count as errors.

Reported numbers are a **conservative lower bound**. Manual review of `llm_response` often looks correct when the strict scorer marks wrong. Use `method1` scraper output as Reuters ground truth.

Retrieval eval is **empirical, not pass/fail** — read AvgLevel, Unjd, and spot-check HTML rather than treating Succ% alone as definitive.

---

## Models & configuration

| Component | Config | Default model |
|-----------|--------|---------------|
| Retrieval ladder | `retrieval/config/settings.py` | `anthropic/claude-sonnet-4.6` |
| HTML extraction | `method2/config/settings.py` | `meta-llama/llama-3.1-8b-instruct` |
| Screenshot extraction | `method3/config/settings.py` | `mistralai/mistral-small-3.2-24b-instruct` |
| Web search | `websearch/config/settings.py` | `openai/gpt-4o-search-preview-2025-03-11` |

All LLM calls use [OpenRouter](https://openrouter.ai/). Retrieval pricing is fetched live at startup.

---

## Project structure

| Path | Purpose |
|------|---------|
| `app.py` | Interactive launcher (retrieval + extraction) |
| `launcher/` | Shared launcher utilities, temp dir |
| `urls/` | Full URL lists for retrieval eval sampling |
| `sample_data/` | Bundled HTML for extraction eval |
| `retrieval/` | Retrieval ladder |
| `retrieval/eval.py` | One-command retrieval eval |
| `retrieval/eval_urls/` | Sampled eval URL lists (5 domains) |
| `retrieval/scripts/sample_eval_urls.py` | Regenerate eval URL samples |
| `retrieval/tests/` | Unit tests (58 tests) |
| `retrieval/IMPLEMENTATION_SPEC.md` | Retrieval design spec |
| `method1/` | Site-specific BeautifulSoup scrapers (6 sites) |
| `method2/` | HTML cleaning + LLM |
| `method3/` | Screenshot + vision LLM |
| `websearch/` | Naive AI web-search extractor (`websearch_extractor.py`) |

---

## Troubleshooting

| Problem | Likely cause | Fix |
|---------|-------------|-----|
| `OPENROUTER_API_KEY not set` | Missing env var | Add to `.env` |
| `Pricing fetched... not found` at startup | Wrong model slug or bad key | Check `LLM_MODEL` in settings; verify key |
| All levels failed | Blocking, missing ScrapingBee key, API limit | Set `SCRAPINGBEE_API_KEY`; check logs |
| High AvgLevel on easy domains | Judge false-rejects | Review `judge_reject` reasons in results JSON |
| Succ% looks good but pages are shells | Judge false-accept | Open accepted HTML on JS domains manually |
| Nonzero **Unjd** in summary | Judge was unreachable during run | Re-run or discount those successes |
| Playwright errors on L3 | Chromium missing | `playwright install chromium` |
| Scraper nulls on some pages | Saved HTML layout differs or field absent | Check `extracted_data`; compare with live page at save time (if possible) |

---

