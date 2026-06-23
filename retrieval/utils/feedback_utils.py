from config import settings
from utils.failure_kind import FETCH_ERROR, JUDGE_REJECT, TRANSIENT_EXHAUSTED


def _format_attempt_line(h: dict) -> str:
    label = settings.LEVEL_LABELS[h["level"]]
    err = (h.get("error") or "unknown error")[:300]
    bytes_written = h.get("bytes_written", 0)
    http_status = h.get("http_status")
    kind = h.get("failure_kind", FETCH_ERROR)

    if kind == JUDGE_REJECT:
        return (
            f"  • {label}: fetched {bytes_written:,} bytes but it was not real page "
            f"content — {err}"
        )

    if kind == TRANSIENT_EXHAUSTED:
        return (
            f"  • {label}: hit repeated transient failures and could not get a clean "
            f"response — {err}"
        )


    if http_status is not None and http_status != 200:
        return f"  • {label}: received HTTP {http_status} — {err}"
    if bytes_written > 0:
        return (
            f"  • {label}: fetched {bytes_written:,} bytes but retrieval failed — {err}"
        )
    if http_status is not None:
        return f"  • {label}: received HTTP {http_status} — {err}"
    return f"  • {label}: failed before a successful HTTP response — {err}"


def build_failure_feedback(history: list) -> str:

    lines = ["Previous retrieval attempts for this URL have failed:"]
    for h in history:
        if h.get("success"):
            continue
        lines.append(_format_attempt_line(h))
    lines.append(
        "Use this information to write a more capable retrieval script "
        "at the next infrastructure level."
    )
    return "\n".join(lines)
