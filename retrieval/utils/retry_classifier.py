from utils.failure_code import TRANSIENT_CODES

TRANSIENT = "transient"
DETERMINISTIC = "deterministic"


def classify_retry_outcome(
    *,
    http_status: int | None,
    failure_code: str | None = None,
    content_rejected: bool = False,
) -> str:


    if content_rejected:
        return DETERMINISTIC

    if http_status is not None:
        if http_status in (401, 403):
            return DETERMINISTIC
        if http_status == 429:
            return TRANSIENT
        if http_status >= 500:
            return TRANSIENT
        if 200 <= http_status < 300:
            return DETERMINISTIC
        if 400 <= http_status < 500:
            return DETERMINISTIC
        return DETERMINISTIC

    if failure_code in TRANSIENT_CODES:
        return TRANSIENT

    return DETERMINISTIC
