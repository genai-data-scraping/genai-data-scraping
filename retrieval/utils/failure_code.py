TIMEOUT = "timeout"
CONNECTION_ERROR = "connection_error"
HTTP_ERROR = "http_error"
SCRIPT_ERROR = "script_error"


NO_OUTPUT = "no_output"
CONTRACT_VIOLATION = "contract_violation"
JSON_PARSE_ERROR = "json_parse_error"
HTML_FILE_MISSING = "html_file_missing"
HTML_FILE_EMPTY = "html_file_empty"
HTML_READ_ERROR = "html_read_error"
RUNNER_EXCEPTION = "runner_exception"
CONTENT_REJECTED = "content_rejected"
CONFIG_ERROR = "config_error"

SCRIPT_REPORTED_CODES = frozenset({
    TIMEOUT,
    CONNECTION_ERROR,
    HTTP_ERROR,
    SCRIPT_ERROR,
})

TRANSIENT_CODES = frozenset({
    TIMEOUT,
    CONNECTION_ERROR,
})


def normalize_script_failure_code(raw: str | None) -> str:

    if raw in SCRIPT_REPORTED_CODES:
        return raw
    return SCRIPT_ERROR
