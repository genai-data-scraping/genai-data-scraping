import json
import os
import subprocess
import sys
import time
import tempfile

from openai import OpenAI

from config import settings
from launcher.project_tmp import TMP_DIR
from utils.logging_utils import filter_html, tprint, tprint_block


def get_client(site: str) -> OpenAI:
    return OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=settings.OPENROUTER_API_KEY or "MISSING_KEY",
        default_headers={
            "HTTP-Referer": settings.OPENROUTER_REFERER,
            "X-Title": settings.openrouter_app_title(site),
        },
    )


def fetch_llm_pricing():

    import urllib.request

    try:
        req = urllib.request.Request(
            "https://openrouter.ai/api/v1/models",
            headers={"Authorization": f"Bearer {settings.OPENROUTER_API_KEY}"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
        for model in data.get("data", []):
            if model.get("id") == settings.LLM_MODEL:
                pricing = model.get("pricing", {})
                settings.LLM_COST_PER_TOKEN_INPUT = float(
                    pricing.get("prompt", settings.LLM_COST_PER_TOKEN_INPUT)
                )
                settings.LLM_COST_PER_TOKEN_OUTPUT = float(
                    pricing.get("completion", settings.LLM_COST_PER_TOKEN_OUTPUT)
                )
                print(
                    f"  Pricing fetched for {settings.LLM_MODEL}: "
                    f"${settings.LLM_COST_PER_TOKEN_INPUT * 1e6:.4f}/M in, "
                    f"${settings.LLM_COST_PER_TOKEN_OUTPUT * 1e6:.4f}/M out"
                )
                return
        print(
            f"  Warning: {settings.LLM_MODEL} not found in OpenRouter models list "
            "— using fallback pricing."
        )
    except Exception as e:
        print(f"  Warning: could not fetch live pricing ({e}) — using fallback pricing.")


def llm_generate(client, messages, llm_calls, level, domain) -> tuple:

    llm_calls[0] += 1
    call_num = llm_calls[0]

    tprint(
        f"\n  [{domain}] ── LLM CALL #{call_num} "
        f"({settings.LEVEL_LABELS[level]}) ──────────────────────────"
    )
    tprint_block("Last user message:", messages[-1]["content"], domain)

    resp = client.chat.completions.create(
        model=settings.LLM_MODEL,
        max_tokens=settings.MAX_CODE_TOKENS,
        messages=messages,
    )
    code = resp.choices[0].message.content.strip()

    input_tokens = resp.usage.prompt_tokens if resp.usage else 0
    output_tokens = resp.usage.completion_tokens if resp.usage else 0
    call_cost = (
        input_tokens * settings.LLM_COST_PER_TOKEN_INPUT
        + output_tokens * settings.LLM_COST_PER_TOKEN_OUTPUT
    )
    tprint(
        f"  [{domain}] Tokens: {input_tokens} in / {output_tokens} out "
        f"→ ${call_cost:.6f}"
    )
    tprint_block(f"RAW LLM RESPONSE (call #{call_num}):", code, domain)

    if code.startswith("```"):
        code = "\n".join(code.split("\n")[1:])
    if code.rstrip().endswith("```"):
        code = "\n".join(code.rstrip().split("\n")[:-1])
    code = code.strip()

    tprint_block(f"CLEANED CODE (call #{call_num}):", code, domain)
    return code, call_cost


def llm_select_level(client, url, domain, untried, history, llm_calls) -> tuple:

    options = "\n".join(f"  - {settings.LEVEL_DESCRIPTIONS[lvl]}" for lvl in untried)
    parts = [
        f"URL: {url}",
        f"Domain: {domain}",
        "",
        "Available levels to choose from (pick exactly one key):",
        options,
    ]
    if history:
        from utils.feedback_utils import build_failure_feedback

        parts += ["", build_failure_feedback(history)]
    parts += ["", "Which level should I try next? Reply with only the level key."]
    user_content = "\n".join(parts)

    messages = [
        {"role": "system", "content": settings.SELECTOR_SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]

    llm_calls[0] += 1
    call_num = llm_calls[0]
    tprint(f"\n  [{domain}] ── LLM CALL #{call_num} (level selection) ──────────────────")
    tprint_block("Selector prompt:", user_content, domain)

    resp = client.chat.completions.create(
        model=settings.LLM_MODEL,
        max_tokens=20,
        messages=messages,
    )
    raw = (resp.choices[0].message.content or "").strip()

    input_tokens = resp.usage.prompt_tokens if resp.usage else 0
    output_tokens = resp.usage.completion_tokens if resp.usage else 0
    call_cost = (
        input_tokens * settings.LLM_COST_PER_TOKEN_INPUT
        + output_tokens * settings.LLM_COST_PER_TOKEN_OUTPUT
    )
    tprint(
        f"  [{domain}] Selector replied: {raw!r} "
        f"({input_tokens} in / {output_tokens} out → ${call_cost:.6f})"
    )

    chosen = None
    lowered = raw.lower()
    for lvl in untried:
        if lvl in lowered:
            chosen = lvl
            break
    if chosen is None:
        for lvl in untried:
            tag = settings.LEVEL_LABELS[lvl].split(":")[0].lower()
            if tag and tag in lowered:
                chosen = lvl
                break
    if chosen is None:
        chosen = untried[0]
        tprint(
            f"  [{domain}] ⚠ Could not parse a level from selector reply; "
            f"defaulting to {settings.LEVEL_LABELS[chosen]}."
        )
    else:
        tprint(f"  [{domain}] Selector chose: {settings.LEVEL_LABELS[chosen]}")

    return chosen, call_cost


def _parse_agent_action(raw: str, available: list) -> tuple:


    import json
    import re

    text = raw.strip()
    if text.startswith("```"):
        text = "\n".join(text.split("\n")[1:])
        if text.rstrip().endswith("```"):
            text = "\n".join(text.rstrip().split("\n")[:-1])
        text = text.strip()


    try:
        obj = json.loads(text)
        action = (obj.get("action") or "").lower()
        if action == "scrapingbee" and "scrapingbee" in available:
            return "scrapingbee", "scrapingbee"
        if action == "code":
            level = (obj.get("level") or "").lower()
            for opt in available:
                if opt == level:
                    return "code", opt
            for opt in available:
                if opt in level or level in opt:
                    return "code", opt
    except (json.JSONDecodeError, AttributeError):
        pass

    lowered = text.lower()
    if "scrapingbee" in lowered and "scrapingbee" in available:
        return "scrapingbee", "scrapingbee"
    for opt in available:
        if opt in lowered:
            return "code", opt
    for opt in available:
        tag = settings.LEVEL_LABELS.get(opt, "").split(":")[0].lower()
        if tag and tag in lowered:
            return "code", opt

    fallback = available[0]
    action = "scrapingbee" if fallback == "scrapingbee" else "code"
    return action, fallback


def llm_select_action(client, url, domain, available, history, llm_calls) -> tuple:


    from utils.feedback_utils import build_failure_feedback

    options = []
    for opt in available:
        if opt == "scrapingbee":
            options.append(
                f"  - code at {settings.LEVEL_DESCRIPTIONS[opt]}"
            )
        else:
            options.append(f"  - code at {settings.LEVEL_DESCRIPTIONS[opt]}")

    parts = [
        f"URL: {url}",
        f"Domain: {domain}",
        "",
        "Available actions (pick exactly one):",
        *options,
    ]
    if history:
        parts += ["", build_failure_feedback(history)]
    parts += [
        "",
        "Reply with ONLY JSON, e.g.:",
        '  {"action": "code", "level": "requests_basic"}',
        '  {"action": "scrapingbee"}',
    ]
    user_content = "\n".join(parts)

    messages = [
        {"role": "system", "content": settings.AGENT_SELECTOR_SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]

    llm_calls[0] += 1
    call_num = llm_calls[0]
    tprint(f"\n  [{domain}] ── LLM CALL #{call_num} (agent action selection) ───────")
    tprint_block("Agent selector prompt:", user_content, domain)

    resp = client.chat.completions.create(
        model=settings.LLM_MODEL,
        max_tokens=80,
        messages=messages,
    )
    raw = (resp.choices[0].message.content or "").strip()

    input_tokens = resp.usage.prompt_tokens if resp.usage else 0
    output_tokens = resp.usage.completion_tokens if resp.usage else 0
    call_cost = (
        input_tokens * settings.LLM_COST_PER_TOKEN_INPUT
        + output_tokens * settings.LLM_COST_PER_TOKEN_OUTPUT
    )
    tprint(
        f"  [{domain}] Agent replied: {raw!r} "
        f"({input_tokens} in / {output_tokens} out → ${call_cost:.6f})"
    )

    action, level = _parse_agent_action(raw, available)
    if action == "scrapingbee":
        tprint(f"  [{domain}] Agent chose: ScrapingBee tool")
    else:
        tprint(f"  [{domain}] Agent chose: code at {settings.LEVEL_LABELS[level]}")

    return action, level, call_cost
