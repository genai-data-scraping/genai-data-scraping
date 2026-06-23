import random
import time

from config import settings
from utils.logging_utils import style, tprint


def max_attempts_for_level(level: str) -> int:
    if level == "scrapingbee":
        return settings.RETRY_MAX_ATTEMPTS_L4
    return settings.RETRY_MAX_ATTEMPTS_CODE


def backoff_seconds(
    attempt_index: int,
    level: str,
    retry_after_seconds: float | None = None,
) -> float:


    base = settings.RETRY_BACKOFF_BASE_SECONDS
    delay = base * (2 ** attempt_index)
    if level == "scrapingbee":
        delay = min(delay, settings.RETRY_BACKOFF_MAX_SECONDS)
    if retry_after_seconds is not None:
        delay = max(delay, retry_after_seconds)
    jitter = delay * settings.RETRY_JITTER_FRACTION
    return max(0.0, delay + random.uniform(-jitter, jitter))


def sleep_before_retry(
    domain: str,
    level_label: str,
    attempt: int,
    max_attempts: int,
    reason: str,
    delay_s: float,
) -> None:
    tprint(
        style(
            f"  ↻ [{domain}] {level_label} retry {attempt + 1}/{max_attempts} "
            f"after {delay_s:.1f}s ({reason})",
            "retry",
        )
    )
    time.sleep(delay_s)
