from config import settings
from services.execution_result import ExecutionResult
from utils.failure_kind import (
    FETCH_ERROR,
    TRANSIENT_EXHAUSTED,
    classify_failure_kind,
)
from utils.retry_classifier import DETERMINISTIC, TRANSIENT, classify_retry_outcome
from utils.retry_utils import backoff_seconds, max_attempts_for_level, sleep_before_retry


def _retry_reason(result: ExecutionResult) -> str:
    if result.http_status is not None:
        return f"HTTP {result.http_status}"
    if result.failure_code:
        return result.failure_code.replace("_", " ")
    return "transient error"


def run_with_retries(
    domain: str,
    level: str,
    execute_once,
) -> tuple[ExecutionResult, str | None]:


    label = settings.LEVEL_LABELS[level]
    max_attempts = max_attempts_for_level(level)
    last = ExecutionResult(success=False, error="No attempts made.")

    for attempt in range(1, max_attempts + 1):
        last = execute_once()

        if last.success:
            return last, None

        outcome = classify_retry_outcome(
            http_status=last.http_status,
            failure_code=last.failure_code,
            content_rejected=last.content_rejected,
        )

        if outcome == DETERMINISTIC:
            failure_kind = classify_failure_kind(
                http_status=last.http_status,
                bytes_written=len(last.html) if last.html else 0,
                content_rejected=last.content_rejected,
            )
            return last, failure_kind

        if attempt < max_attempts:
            delay = backoff_seconds(
                attempt - 1,
                level,
                retry_after_seconds=last.retry_after_seconds,
            )
            sleep_before_retry(
                domain,
                label,
                attempt,
                max_attempts,
                _retry_reason(last),
                delay,
            )
            continue

        return last, TRANSIENT_EXHAUSTED

    return last, FETCH_ERROR
