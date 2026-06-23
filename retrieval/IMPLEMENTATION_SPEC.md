# Retrieval Ladder — Implementation Spec

Steps 1–9 are merged in code.

## Landed contract (steps 1–3)

- Generated code writes HTML to `os.environ['RETRIEVAL_HTML_PATH']` and prints **one** status-JSON line.
- Status JSON fields: `success`, `bytes_written`, `error`, `http_status`, `failure_code`, `retry_after_seconds` (optional).
- **Transient retry = re-execute the same generated script, no new LLM call.** One generation per rung, up to N executions of that generation with backoff.
- `execute_code` returns an **`ExecutionResult` dataclass** (not a tuple): `success`, `html`, `error`, `http_status`, `failure_code`, `content_rejected`, `retry_after_seconds`.
- Failed history entries carry `failure_kind` ∈ {`fetch_error`, `judge_reject`, `transient_exhausted`}, plus `http_status`, `bytes_written`.
- **`judge_retrieval(html, url)`** replaces `validate_html` / `MIN_HTML_CHARS` / `BOT_SIGNALS`. `judge_reject` is set only from the judge's verdict (`content_rejected=True`), never from byte thresholds.

## Design in one line

Fixed `L1→L2→L3→L4` loop. Each rung: LLM generates code once → execute (with same-rung retries on transient failures) → escalate on deterministic failure or exhausted retries. LLM judge (step 4) gives binary success verdict. **The LLM writes code; it never decides routing.**

## Guardrails

- **Retry classifier** keys off `http_status` + typed **`failure_code`** from the subprocess/runner — **never substring search of the human-readable `error` string.**
- Transient/deterministic split is not an LLM call and not a site list.
- Fixed `L1→L2→L3→L4` in ladder mode. `failure_kind` is feedback metadata only — if you write `if failure_kind == ...: escalate`, stop.
- **`judge_reject`** (step 4) is set only when **the judge's verdict** says reject — never from byte thresholds or `http_status == 200 and bytes < X`.
- Deterministic failure never consumes transient retry budget.
- No "100%" language in logs or comments.

## Typed failure codes (`utils/failure_code.py`)

| Code | Transient? | Set by |
|---|---|---|
| `timeout` | yes | runner or script |
| `connection_error` | yes | runner or script |
| `http_error` | via `http_status` | script / ScrapingBee |
| `script_error` | no | script default |
| `contract_violation` | no | runner |
| `content_rejected` | no | judge verdict (step 4) |

- **`judge_retrieval`** returns `JudgeResult`. Unparseable → fail closed (`content_rejected`). Infra unreachable after `JUDGE_MAX_ATTEMPTS` → lean accept (`judge_unavailable=True`) with loud console warning.

## Step 6 — L4 via code-gen (signed)

- All rungs including L4 route through `_attempt_code_level` → `execute_code` → judge.
- `scrapingbee_service.py` and `_FETCH_PROFILES` deleted.

### L4 param-variation line — accurate scope

The `LEVEL_PROMPTS["scrapingbee"]` param-variation instruction **conditions the single L4 codegen pass on prior L1–L3 failure context** (e.g. pick `stealth_proxy` after L3 hit Cloudflare). It does **not** reproduce `_FETCH_PROFILES`'s within-L4 sequential escalation (premium → premium+US-geo → stealth). L4 code is generated once per URL; same-rung transient retries re-execute that same script (step 3 contract). Eval decides whether one LLM-chosen param set is sufficient.

## Steps 7–9 (landed)

| Step | What |
|---|---|
| **7** | `INTER_URL_DELAY_SECONDS` (default 2.0) — sleep between URLs in `run_domain`, not before the first |
| **8** | Console UX — `[Lx/4]` rung tags, colored success/fail/retry/escalate/warn via `style()` in `logging_utils.py` (`isatty()`-aware, thread-safe through `tprint` lock) |
| **9** | `LLM_MODEL = anthropic/claude-sonnet-4.6`; `DEFAULT_MODE = ladder` |

## Eval

Run on five domains (amazon, cars, reuters, wikipedia, yahoo) after full build. Upwork excluded from retrieval evals. Read: AvgLevel per domain, `Unjd` count, spot-check judge rejects and JS-domain accepts.
