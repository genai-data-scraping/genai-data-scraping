import json
import os
import subprocess
import sys
import time
import tempfile
import uuid

from config import settings
from launcher.project_tmp import TMP_DIR
from services.execution_result import ExecutionResult
from services.judge_service import JudgeResult, judge_retrieval
from utils.failure_code import (
    CONNECTION_ERROR,
    CONTENT_REJECTED,
    CONTRACT_VIOLATION,
    HTML_FILE_EMPTY,
    HTML_FILE_MISSING,
    HTML_READ_ERROR,
    HTTP_ERROR,
    JSON_PARSE_ERROR,
    NO_OUTPUT,
    RUNNER_EXCEPTION,
    SCRIPT_ERROR,
    TIMEOUT,
    normalize_script_failure_code,
)
from utils.logging_utils import style, tprint, tprint_block


def _failure(
    error: str,
    failure_code: str,
    http_status: int | None = None,
    html: str = "",
    content_rejected: bool = False,
    retry_after_seconds: float | None = None,
) -> ExecutionResult:
    return ExecutionResult(
        success=False,
        html=html,
        error=error,
        http_status=http_status,
        failure_code=failure_code,
        content_rejected=content_rejected,
        retry_after_seconds=retry_after_seconds,
    )


def _minimal_subprocess_env(html_path: str) -> dict:

    env = {
        "PATH": os.environ.get("PATH", ""),
        settings.RETRIEVAL_HTML_PATH_ENV: html_path,
    }
    if settings.SCRAPINGBEE_API_KEY:
        env["SCRAPINGBEE_API_KEY"] = settings.SCRAPINGBEE_API_KEY
    return env


def _parse_status_json(output: str) -> tuple[dict | None, str | None]:


    lines = [ln.strip() for ln in output.splitlines() if ln.strip()]
    if not lines:
        return None, "No JSON status line in subprocess stdout."

    if len(lines) > 1:
        return None, (
            f"Script violated output contract: expected exactly one stdout line, "
            f"got {len(lines)} non-empty line(s). HTML must not be printed to stdout."
        )

    json_str = lines[0]
    if not json_str.startswith("{"):
        return None, (
            "Script violated output contract: stdout line is not JSON status "
            f"(starts with {json_str[:40]!r})."
        )

    try:
        return json.loads(json_str), None
    except json.JSONDecodeError as e:
        return None, f"JSON parse error: {e}. Raw: {json_str[:200]}"


def _read_html_file(
    html_path: str, domain: str, bytes_written: int
) -> tuple[str | None, str | None, str | None]:

    if not os.path.isfile(html_path):
        msg = (
            "Script reported success but never wrote the HTML file "
            f"(expected at {html_path!r}, bytes_written={bytes_written:,})."
        )
        tprint(f"  [{domain}] {style('✗ FAILURE:', 'fail')} {msg}")
        return None, msg, HTML_FILE_MISSING

    try:
        with open(html_path, encoding="utf-8") as fh:
            html = fh.read()
    except OSError as e:
        msg = f"Could not read HTML file: {e}"
        tprint(f"  [{domain}] {style('✗ FAILURE:', 'fail')} {msg}")
        return None, msg, HTML_READ_ERROR

    if not html:
        msg = (
            "Script reported success but wrote an empty HTML file "
            f"(bytes_written={bytes_written:,})."
        )
        tprint(f"  [{domain}] {style('✗ FAILURE:', 'fail')} {msg}")
        return None, msg, HTML_FILE_EMPTY

    return html, None, None


def _allocate_html_path() -> str:

    return str(TMP_DIR / f"retrieval-{uuid.uuid4().hex}.html")


def _parse_retry_after(value) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _script_failure_code(result: dict) -> str:
    normalized = normalize_script_failure_code(result.get("failure_code"))
    if result.get("http_status") is not None and normalized == SCRIPT_ERROR:
        return HTTP_ERROR
    return normalized


def _apply_judge_result(
    judge: JudgeResult,
    html: str,
    http_status: int | None,
    domain: str,
) -> ExecutionResult:
    if judge.judge_unavailable:
        return ExecutionResult(
            success=True,
            html=html,
            http_status=http_status,
            judge_unavailable=True,
            llm_cost_usd=judge.cost,
        )

    if not judge.ok:
        tprint(f"  [{domain}] {style('✗', 'fail')} {judge.reason}")
        return _failure(
            judge.reason,
            CONTENT_REJECTED,
            http_status=http_status,
            html=html,
            content_rejected=True,
        )

    tprint(
        f"  [{domain}] {style('✓ SUCCESS:', 'success')} "
        f"{len(html):,} bytes of HTML retrieved."
    )
    return ExecutionResult(
        success=True,
        html=html,
        http_status=http_status,
        llm_cost_usd=judge.cost,
    )


def execute_code(
    code: str,
    domain: str,
    level: str,
    url: str,
    client,
    llm_calls: list,
) -> ExecutionResult:

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, dir=str(TMP_DIR)
    ) as f:
        f.write(code)
        script_path = f.name

    html_path = _allocate_html_path()

    tprint(f"  [{domain}] Executing subprocess: {script_path}")
    tprint(f"  [{domain}] HTML output path: {html_path}")
    t_exec = time.time()
    proc = None

    try:
        proc = subprocess.run(
            [sys.executable, script_path],
            capture_output=True,
            text=True,
            timeout=settings.URL_TIMEOUT,
            env=_minimal_subprocess_env(html_path),
        )
        elapsed_exec = round(time.time() - t_exec, 1)
        tprint(
            f"  [{domain}] Subprocess finished in {elapsed_exec}s "
            f"(return code: {proc.returncode})"
        )

        if proc.stderr.strip():
            tprint_block("SUBPROCESS STDERR:", proc.stderr.strip(), domain)
        else:
            tprint(f"  [{domain}] (no stderr)")

        output = (proc.stdout or "").strip()
        if output:
            tprint_block("SUBPROCESS STDOUT:", output, domain)
        else:
            tprint(f"  [{domain}] (no stdout)")

        if not output:
            hint = (proc.stderr or "").strip()[:400]
            msg = f"No output from subprocess.{' stderr: ' + hint if hint else ''}"
            tprint(f"  [{domain}] {style('✗ FAILURE:', 'fail')} {msg}")
            return _failure(msg, NO_OUTPUT)

        result, parse_err = _parse_status_json(output)
        if parse_err:
            tprint(f"  [{domain}] {style('✗ FAILURE:', 'fail')} {parse_err}")
            code = (
                JSON_PARSE_ERROR
                if parse_err.startswith("JSON parse error")
                else CONTRACT_VIOLATION
            )
            return _failure(parse_err, code)

        http_status = result.get("http_status")
        retry_after = _parse_retry_after(result.get("retry_after_seconds"))
        bytes_written = result.get("bytes_written", 0)
        tprint(
            f"  [{domain}] Script reported success={result.get('success')}, "
            f"bytes_written={bytes_written:,}, http_status={http_status}, "
            f"error={str(result.get('error') or 'None')[:150]}"
        )

        if not result.get("success"):
            msg = result.get("error") or "Script reported failure (no error message)."
            tprint(f"  [{domain}] {style('✗ SCRIPT FAILURE:', 'fail')} {msg}")
            return _failure(
                msg,
                _script_failure_code(result),
                http_status=http_status,
                retry_after_seconds=retry_after,
            )

        html, read_err, read_code = _read_html_file(html_path, domain, bytes_written)
        if read_err:
            return _failure(read_err, read_code, http_status=http_status)

        judge = judge_retrieval(client, html, url, domain, llm_calls)
        return _apply_judge_result(judge, html, http_status, domain)

    except subprocess.TimeoutExpired:
        elapsed_exec = round(time.time() - t_exec, 1)
        msg = f"Timed out after {settings.URL_TIMEOUT}s (exec took {elapsed_exec}s)."
        tprint(f"  [{domain}] {style('✗ TIMEOUT:', 'fail')} {msg}")
        return _failure(msg, TIMEOUT)
    except Exception as e:
        msg = str(e)
        tprint(f"  [{domain}] {style('✗ EXCEPTION', 'fail')} during subprocess: {msg}")
        return _failure(msg, RUNNER_EXCEPTION)
    finally:
        for path in (script_path, html_path):
            try:
                os.unlink(path)
            except OSError:
                pass
