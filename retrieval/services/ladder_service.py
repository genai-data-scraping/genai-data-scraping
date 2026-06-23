import time
from collections import defaultdict

from config import settings
from services.execution_service import execute_code
from services.llm_service import (
    get_client,
    llm_generate,
    llm_select_action,
    llm_select_level,
)
from services.storage_service import save_html
from utils.feedback_utils import build_failure_feedback
from utils.logging_utils import style, tprint
from utils.retry_loop import run_with_retries


def _untried_levels(tried: list) -> list:

    levels = [lvl for lvl in settings.LEVELS if lvl not in tried]
    if not settings.SCRAPINGBEE_API_KEY:
        levels = [lvl for lvl in levels if lvl != "scrapingbee"]
    return levels


def _available_actions(tried: list) -> list:

    available = [lvl for lvl in settings.CODE_LEVELS if lvl not in tried]
    if not settings.SCRAPINGBEE_API_KEY:
        available = [lvl for lvl in available if lvl != "scrapingbee"]
    return available


def _rung_tag(level: str) -> str:
    idx = settings.LEVELS.index(level) + 1 if level in settings.LEVELS else 4
    return f"L{idx}/4"


def _attempt_code_level(
    url, domain, level, messages, client, llm_calls, history
) -> tuple:


    level_instruction = settings.LEVEL_PROMPTS[level].format(url=url)
    if history:
        user_content = f"{build_failure_feedback(history)}\n\n{level_instruction}"
    else:
        user_content = level_instruction

    messages.append({"role": "user", "content": user_content})

    code, call_cost = llm_generate(client, messages, llm_calls, level, domain)
    messages.append({"role": "assistant", "content": code})

    judge_cost = [0.0]

    def _run_once():
        result = execute_code(code, domain, level, url, client, llm_calls)
        judge_cost[0] += result.llm_cost_usd
        return result

    result, failure_kind = run_with_retries(domain, level, _run_once)
    return (
        result.success,
        result.html,
        result.error,
        call_cost + judge_cost[0],
        result.http_status,
        failure_kind,
        result.judge_unavailable,
    )


def _record_attempt(
    history,
    level,
    success,
    html,
    error,
    elapsed_s,
    http_status=None,
    failure_kind=None,
    bytes_written=None,
):
    entry = {
        "level": level,
        "success": success,
        "error": error[:400] if error else None,
        "bytes_written": bytes_written if bytes_written is not None else (len(html) if html else 0),
        "http_status": http_status,
        "elapsed_s": elapsed_s,
    }
    if not success:
        entry["failure_kind"] = failure_kind
    history.append(entry)


def _success_result(
    url, domain, level, history, llm_calls, llm_cost_usd, t0, html, judge_unavailable=False
):
    elapsed = round(time.time() - t0, 1)
    label = settings.LEVEL_LABELS[level]
    html_path = save_html(url, domain, html)
    verdict_note = (
        style("  ⚠ accepted without judge verdict", "warn") if judge_unavailable else ""
    )
    tprint(
        f"\n  {style('✓', 'success')} [{domain}] {label} — {len(html):,} chars — "
        f"{llm_calls[0]} LLM calls — LLM cost ${llm_cost_usd:.6f} — {elapsed}s total"
        f"{verdict_note}"
    )
    level_index = settings.LEVELS.index(level) + 1 if level in settings.LEVELS else 4
    return {
        "url": url,
        "domain": domain,
        "success": True,
        "level": level,
        "level_index": level_index,
        "level_label": label,
        "llm_calls": llm_calls[0],
        "elapsed_s": elapsed,
        "html_chars": len(html),
        "html_path": html_path,
        "llm_cost_usd": round(llm_cost_usd, 6),
        "judge_unavailable": judge_unavailable,
        "history": history,
    }


def _failure_result(url, domain, history, llm_calls, llm_cost_usd, t0):
    elapsed = round(time.time() - t0, 1)
    tprint(f"\n{style('━' * 70, 'dim')}")
    tprint(f"  {style('✗', 'fail')} [{domain}] ALL LEVELS FAILED for: {url}")
    tprint(
        f"  [{domain}] Total elapsed: {elapsed}s | LLM calls: {llm_calls[0]} | "
        f"LLM cost: ${llm_cost_usd:.6f}"
    )
    tprint(f"  [{domain}] Failure summary:")
    for h in history:
        tprint(
            f"    • {settings.LEVEL_LABELS[h['level']]:35s} → "
            f"{h['error'][:100] if h['error'] else 'no error'}"
        )
    tprint(f"{style('━' * 70, 'dim')}")
    return {
        "url": url,
        "domain": domain,
        "success": False,
        "level": "all_failed",
        "level_index": 5,
        "level_label": "All levels failed",
        "llm_calls": llm_calls[0],
        "elapsed_s": elapsed,
        "html_chars": 0,
        "html_path": None,
        "llm_cost_usd": round(llm_cost_usd, 6),
        "judge_unavailable": False,
        "history": history,
    }


def run_ladder(url: str, domain: str, mode: str = None) -> dict:


    mode = mode or settings.DEFAULT_MODE
    llm_calls = [0]
    llm_cost_usd = 0.0
    t0 = time.time()
    history = []
    tried = []
    client = get_client(domain)
    messages = [{"role": "system", "content": settings.SYSTEM_PROMPT}]

    tprint(f"\n{style('━' * 70, 'dim')}")
    tprint(f"  [{domain}] Starting retrieval for URL: {url}  (mode: {mode})")
    tprint(f"{style('━' * 70, 'dim')}")

    while True:
        if mode == "ladder":
            untried = _untried_levels(tried)
            if not untried:
                break
            level = untried[0]

        elif mode == "llm":
            untried = _untried_levels(tried)
            if not untried:
                break
            level, sel_cost = llm_select_level(
                client, url, domain, untried, history, llm_calls
            )
            llm_cost_usd += sel_cost

        elif mode == "agent":
            available = _available_actions(tried)
            if not available:
                break
            action, level, sel_cost = llm_select_action(
                client, url, domain, available, history, llm_calls
            )
            llm_cost_usd += sel_cost
            if action == "scrapingbee":
                level = "scrapingbee"


        else:
            raise ValueError(f"Unknown retrieval mode: {mode!r}")

        tried.append(level)
        label = settings.LEVEL_LABELS[level]
        rung = _rung_tag(level)
        tprint(
            f"\n  {style('▶', 'rung')} [{domain}] "
            f"{style(f'[{rung}]', 'bold', 'rung')} Attempting {label} ..."
        )

        t_level = time.time()

        (
            success,
            html,
            error,
            call_cost,
            http_status,
            failure_kind,
            judge_unavailable,
        ) = _attempt_code_level(
            url, domain, level, messages, client, llm_calls, history
        )
        llm_cost_usd += call_cost

        level_elapsed = round(time.time() - t_level, 1)
        _record_attempt(
            history,
            level,
            success,
            html,
            error,
            level_elapsed,
            http_status=http_status,
            failure_kind=failure_kind,
        )

        if success:
            return _success_result(
                url,
                domain,
                level,
                history,
                llm_calls,
                llm_cost_usd,
                t0,
                html,
                judge_unavailable=judge_unavailable,
            )

        tprint(
            f"  {style('✗', 'fail')} [{domain}] {label} FAILED in {level_elapsed}s — "
            f"{error[:120]}"
        )
        if mode == "ladder" and _untried_levels(tried):
            tprint(
                style(
                    f"  {style('⬆', 'escalate')} [{domain}] Escalating to next level "
                    f"with failure context...",
                    "escalate",
                )
            )
        elif mode == "llm" and _untried_levels(tried):
            tprint(
                style(
                    f"  [{domain}] Re-selecting next level with failure context...",
                    "escalate",
                )
            )
        elif mode == "agent" and _available_actions(tried):
            tprint(
                style(
                    f"  [{domain}] Re-selecting next action with failure context...",
                    "escalate",
                )
            )

    return _failure_result(url, domain, history, llm_calls, llm_cost_usd, t0)


def run_domain(domain: str, urls: list) -> list:
    results = []
    delay = settings.INTER_URL_DELAY_SECONDS
    for i, url in enumerate(urls):
        if i > 0 and delay > 0:
            tprint(
                style(
                    f"  ⏸ [{domain}] pacing {delay:.1f}s before next URL...",
                    "dim",
                )
            )
            time.sleep(delay)
        results.append(run_ladder(url, domain))
    return results


def write_summary(results: list, out_dir: str):
    by_domain = defaultdict(list)
    for r in results:
        by_domain[r["domain"]].append(r)

    S = "═" * 75
    lines = [
        S,
        "  RETRIEVAL LADDER — RESULTS BY DOMAIN",
        "  (LLM generates code at each level; escalates until success)",
        S,
        f"  {'Domain':<22} {'URLs':>4}  {'Succ%':>6}  "
        f"{'AvgLevel':>9}  {'AvgLLMCost':>11}  {'AvgTime':>9}  "
        f"{'L1':>4}  {'L2':>4}  {'L3':>4}  {'L4':>4}  {'Fail':>4}  {'Unjd':>4}",
        "  " + "─" * 77,
    ]

    totals = {
        "n": 0, "success": 0, "cost": 0.0, "elapsed": 0.0, "level": 0,
        "L1": 0, "L2": 0, "L3": 0, "L4": 0, "fail": 0, "unjudged": 0,
    }

    for domain in sorted(by_domain.keys()):
        runs = by_domain[domain]
        n = len(runs)
        success = [r for r in runs if r["success"]]
        unjudged = [r for r in success if r.get("judge_unavailable")]
        l_counts = defaultdict(int)
        for r in runs:
            l_counts[r["level_index"]] += 1

        avg_level = (
            sum(r["level_index"] for r in success) / len(success) if success else 0
        )
        avg_cost = sum(r["llm_cost_usd"] for r in runs) / n
        avg_time = sum(r["elapsed_s"] for r in runs) / n

        lines.append(
            f"  {domain:<22} {n:>4}  "
            f"{len(success) / n:>5.1%}  "
            f"{avg_level:>9.2f}  "
            f"${avg_cost:>8.4f}  "
            f"{avg_time:>8.1f}s  "
            f"{l_counts[1]:>4}  {l_counts[2]:>4}  "
            f"{l_counts[3]:>4}  {l_counts[4]:>4}  {l_counts[5]:>4}  "
            f"{len(unjudged):>4}"
        )

        totals["n"] += n
        totals["success"] += len(success)
        totals["cost"] += sum(r["llm_cost_usd"] for r in runs)
        totals["elapsed"] += sum(r["elapsed_s"] for r in runs)
        totals["level"] += sum(r["level_index"] for r in success)
        totals["unjudged"] += len(unjudged)
        for k, lbl in [(1, "L1"), (2, "L2"), (3, "L3"), (4, "L4"), (5, "fail")]:
            totals[lbl] += l_counts[k]

    n = totals["n"]
    lines += [
        "  " + "─" * 77,
        f"  {'OVERALL':<22} {n:>4}  "
        f"{totals['success'] / n:>5.1%}  "
        f"{totals['level'] / max(totals['success'], 1):>9.2f}  "
        f"${totals['cost'] / n:>8.4f}  "
        f"{totals['elapsed'] / n:>8.1f}s  "
        f"{totals['L1']:>4}  {totals['L2']:>4}  "
        f"{totals['L3']:>4}  {totals['L4']:>4}  {totals['fail']:>4}  "
        f"{totals['unjudged']:>4}",
        "",
        "  Columns L1–L4: number of URLs successfully retrieved at each level.",
        "  Fail: URLs where all four levels failed.",
        "  Unjd: successful URLs accepted without a judge verdict (judge unavailable).",
        "  AvgLevel computed over successful URLs only.",
        f"  Unjudged total: {totals['unjudged']} page(s) accepted without verdict — "
        "success rate is soft by that count if nonzero.",
        S,
    ]

    report = "\n".join(lines)
    print("\n" + report + "\n")

    path = f"{out_dir.rstrip('/')}/ladder_summary.txt"
    with open(path, "w") as f:
        f.write(report + "\n")
    print(f"Summary saved → {path}")
