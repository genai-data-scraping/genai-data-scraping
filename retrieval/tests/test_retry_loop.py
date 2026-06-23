import sys
import unittest
from pathlib import Path
from unittest.mock import patch

project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from services.execution_result import ExecutionResult
from utils.failure_kind import FETCH_ERROR, JUDGE_REJECT, TRANSIENT_EXHAUSTED
from utils.retry_loop import run_with_retries


class TestRunWithRetries(unittest.TestCase):
    def test_success_on_first_attempt(self):
        results = [ExecutionResult(success=True, html="<html/>", http_status=200)]
        calls = {"n": 0}

        def execute_once():
            out = results[calls["n"]]
            calls["n"] += 1
            return out

        result, failure_kind = run_with_retries("example.com", "requests_basic", execute_once)
        self.assertTrue(result.success)
        self.assertIsNone(failure_kind)
        self.assertEqual(calls["n"], 1)

    def test_retries_transient_then_succeeds(self):
        attempts = [
            ExecutionResult(
                success=False,
                error="HTTP 503",
                http_status=503,
                failure_code="http_error",
            ),
            ExecutionResult(success=True, html="<html/>", http_status=200),
        ]
        calls = {"n": 0}

        def execute_once():
            out = attempts[calls["n"]]
            calls["n"] += 1
            return out

        with patch("utils.retry_loop.sleep_before_retry"):
            result, failure_kind = run_with_retries(
                "example.com", "requests_basic", execute_once
            )
        self.assertTrue(result.success)
        self.assertIsNone(failure_kind)
        self.assertEqual(calls["n"], 2)

    def test_deterministic_403_no_retry(self):
        calls = {"n": 0}

        def execute_once():
            calls["n"] += 1
            return ExecutionResult(
                success=False,
                error="Forbidden",
                http_status=403,
                failure_code="http_error",
            )

        result, failure_kind = run_with_retries(
            "example.com", "requests_headers", execute_once
        )
        self.assertFalse(result.success)
        self.assertEqual(failure_kind, FETCH_ERROR)
        self.assertEqual(calls["n"], 1)

    def test_transient_exhausted_after_budget(self):
        calls = {"n": 0}

        def execute_once():
            calls["n"] += 1
            return ExecutionResult(
                success=False,
                error="HTTP 429",
                http_status=429,
                failure_code="http_error",
            )

        with patch("utils.retry_loop.sleep_before_retry"):
            result, failure_kind = run_with_retries(
                "example.com", "requests_basic", execute_once
            )
        self.assertFalse(result.success)
        self.assertEqual(failure_kind, TRANSIENT_EXHAUSTED)
        self.assertEqual(calls["n"], 3)

    def test_judge_reject_is_deterministic_no_retry(self):
        calls = {"n": 0}

        def execute_once():
            calls["n"] += 1
            return ExecutionResult(
                success=False,
                error="Cloudflare challenge page.",
                http_status=200,
                failure_code="content_rejected",
                content_rejected=True,
                html="<html>challenge</html>",
            )

        result, failure_kind = run_with_retries(
            "example.com", "playwright", execute_once
        )
        self.assertFalse(result.success)
        self.assertEqual(failure_kind, JUDGE_REJECT)
        self.assertEqual(calls["n"], 1)
        calls = {"n": 0}

        def execute_once():
            calls["n"] += 1
            return ExecutionResult(
                success=False,
                error="HTTP 502",
                http_status=502,
                failure_code="http_error",
            )

        with patch("utils.retry_loop.sleep_before_retry"):
            _result, failure_kind = run_with_retries(
                "example.com", "scrapingbee", execute_once
            )
        self.assertEqual(failure_kind, TRANSIENT_EXHAUSTED)
        self.assertEqual(calls["n"], 5)


if __name__ == "__main__":
    unittest.main()
