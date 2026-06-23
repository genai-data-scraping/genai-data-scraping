# Eval URL samples

Five domains: amazon, cars, reuters, wikipedia, yahoo (Upwork excluded).

## Run eval

From `retrieval/`:

```bash
python eval.py          # smoke — 5 URLs per domain (~25 total)
python eval.py full     # full  — 100 URLs per domain (~500 total)
```

That's it — sampling, ladder run, summary table, and one log per domain are all automatic.

**Outputs** (smoke → `results/eval-smoke/`, full → `results/eval/`):

| File | What |
|------|------|
| `ladder_summary.txt` | Summary table by domain |
| `ladder_results.json` | Full per-URL results |
| `logs/*.log` | One log per domain (5 files) |
| `html/<domain>/` | Saved HTML |

**Optional flags:**

```bash
python eval.py full --no-resample   # skip re-sampling; use existing eval_urls/
python eval.py smoke --seed 99      # different random sample
```

**Shell wrapper** (same thing):

```bash
chmod +x eval.sh
./eval.sh
./eval.sh full
```

**Prerequisites:** `OPENROUTER_API_KEY` and `SCRAPINGBEE_API_KEY` in `.env` or environment; `playwright install chromium` for L3.
