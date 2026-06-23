import json
import re
import time

from dataclasses import dataclass

from openai import APIConnectionError, APITimeoutError, OpenAI, RateLimitError

from config import settings
from utils.logging_utils import style, tprint, tprint_block


@dataclass
class JudgeResult:
    ok: bool
    reason: str
    cost: float = 0.0
    content_rejected: bool = False
    judge_unavailable: bool = False


def _judge_sample(html: str) -> str:
    head = html[: settings.JUDGE_HEAD_CHARS]
    mid_start = max(0, len(html) // 2 - settings.JUDGE_MID_HALF_CHARS)
    mid_end = mid_start + settings.JUDGE_MID_SLICE_CHARS
    mid = html[mid_start:mid_end]
    return f"=== HEAD (first ~{settings.JUDGE_HEAD_CHARS} chars) ===\n{head}\n\n=== MID (~{settings.JUDGE_MID_SLICE_CHARS} chars around middle) ===\n{mid}\n"


def _judge_user_message(url: str, html: str) -> str:
    return (
        f"URL: {url}\n"
        f"Total HTML length: {len(html):,} characters\n\n"
        f"{_judge_sample(html)}"
    )


def _parse_judge_response(raw: str) -> tuple[bool | None, str]:

    text = raw.strip()
    if text.startswith("```"):
        text = "\n".join(text.split("\n")[1:])
        if text.rstrip().endswith("```"):
            text = "\n".join(text.rstrip().split("\n")[:-1])
        text = text.strip()

    try:
        obj = json.loads(text)
        ok = obj.get("ok")
        reason = (obj.get("reason") or "").strip()
        if not isinstance(ok, bool):
            return None, "judge unparseable"
        if not reason:
            reason = "Judge returned no reason." if not ok else "Judge accepted page."
        return ok, reason
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            obj = json.loads(match.group(0))
            ok = obj.get("ok")
            reason = (obj.get("reason") or "").strip()
            if isinstance(ok, bool):
                return ok, reason or ("judge unparseable" if not ok else "Judge accepted page.")
        except json.JSONDecodeError:
            pass

    return None, "judge unparseable"


def _is_judge_infra_error(exc: BaseException) -> bool:

    return isinstance(exc, (APIConnectionError, APITimeoutError, RateLimitError))


def _call_judge_api(
    client: OpenAI,
    user_content: str,
    domain: str,
    call_num: int,
) -> tuple[str, float]:

    tprint(
        f"\n  [{domain}] ── LLM JUDGE CALL #{call_num} ─────────────────────────────"
    )
    tprint_block("Judge input (truncated):", user_content[:800] + "...", domain)

    resp = client.chat.completions.create(
        model=settings.LLM_MODEL,
        max_tokens=settings.JUDGE_MAX_TOKENS,
        messages=[
            {"role": "system", "content": settings.JUDGE_SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
    )
    raw = (resp.choices[0].message.content or "").strip()

    input_tokens = resp.usage.prompt_tokens if resp.usage else 0
    output_tokens = resp.usage.completion_tokens if resp.usage else 0
    call_cost = (
        input_tokens * settings.LLM_COST_PER_TOKEN_INPUT
        + output_tokens * settings.LLM_COST_PER_TOKEN_OUTPUT
    )
    tprint(
        f"  [{domain}] Judge tokens: {input_tokens} in / {output_tokens} out "
        f"→ ${call_cost:.6f}"
    )
    tprint_block("Judge raw response:", raw, domain)
    return raw, call_cost


def judge_retrieval(
    client: OpenAI,
    html: str,
    url: str,
    domain: str,
    llm_calls: list,
) -> JudgeResult:


    if not html or not html.strip():
        return JudgeResult(
            ok=False,
            reason="Empty HTML response.",
            content_rejected=True,
        )

    user_content = _judge_user_message(url, html)
    total_cost = 0.0
    last_infra_error = None

    for attempt in range(1, settings.JUDGE_MAX_ATTEMPTS + 1):
        llm_calls[0] += 1
        call_num = llm_calls[0]

        try:
            raw, call_cost = _call_judge_api(client, user_content, domain, call_num)
            total_cost += call_cost
        except Exception as exc:
            if not _is_judge_infra_error(exc):
                raise
            last_infra_error = exc
            tprint(
                f"  [{domain}] {style('✗ JUDGE INFRA ERROR', 'fail')} "
                f"(attempt {attempt}/{settings.JUDGE_MAX_ATTEMPTS}): "
                f"{type(exc).__name__}: {exc}"
            )
            if attempt < settings.JUDGE_MAX_ATTEMPTS:
                time.sleep(settings.JUDGE_RETRY_BACKOFF_SECONDS)
                continue
            tprint(
                style(
                    f"\n  ⚠ [{domain}] judge unavailable — accepted without verdict "
                    f"({type(last_infra_error).__name__} after "
                    f"{settings.JUDGE_MAX_ATTEMPTS} attempts)",
                    "warn",
                )
            )
            return JudgeResult(
                ok=True,
                reason="judge unavailable",
                cost=total_cost,
                judge_unavailable=True,
            )

        ok, reason = _parse_judge_response(raw)
        if ok is None:
            tprint(f"  [{domain}] {style('✗ JUDGE UNPARSEABLE:', 'fail')} {reason}")
            return JudgeResult(
                ok=False,
                reason=reason,
                cost=total_cost,
                content_rejected=True,
            )

        if ok:
            tprint(f"  [{domain}] {style('✓ JUDGE ACCEPT:', 'success')} {reason}")
        else:
            tprint(f"  [{domain}] {style('✗ JUDGE REJECT:', 'fail')} {reason}")

        return JudgeResult(
            ok=ok,
            reason=reason,
            cost=total_cost,
            content_rejected=not ok,
        )


    return JudgeResult(
        ok=True,
        reason="judge unavailable",
        cost=total_cost,
        judge_unavailable=True,
    )
