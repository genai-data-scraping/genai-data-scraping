FETCH_ERROR = "fetch_error"
JUDGE_REJECT = "judge_reject"
TRANSIENT_EXHAUSTED = "transient_exhausted"

ALL_FAILURE_KINDS = (FETCH_ERROR, JUDGE_REJECT, TRANSIENT_EXHAUSTED)


def classify_failure_kind(
    *,
    http_status: int | None,
    bytes_written: int,
    content_rejected: bool = False,
) -> str:


    if content_rejected:
        return JUDGE_REJECT
    return FETCH_ERROR
