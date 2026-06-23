import os
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

project_root = Path(__file__).resolve().parents[1]
repo_root = project_root.parent
sys.path.insert(0, str(repo_root))
sys.path.insert(0, str(project_root))

from launcher.project_tmp import ensure_tmp_dir

ensure_tmp_dir()

from config import settings
from services.execution_service import _minimal_subprocess_env, _parse_status_json, execute_code
from services.judge_service import JudgeResult


LARGE_HTML_BYTES = 5 * 1024 * 1024

SUCCESS_SCRIPT = """
import json
import os

html_path = os.environ[{env_key!r}]
html = "<html><body>" + ("x" * 50001) + "</body></html>"
with open(html_path, "w", encoding="utf-8") as fh:
    fh.write(html)
print(json.dumps({{
    "success": True,
    "bytes_written": len(html),
    "error": None,
    "http_status": 200,
}}))
"""


LARGE_SUCCESS_SCRIPT = """
import json
import os

html_path = os.environ[{env_key!r}]
payload_size = {payload_size}
html = "<html><body>" + ("y" * payload_size) + "</body></html>"
with open(html_path, "w", encoding="utf-8") as fh:
    fh.write(html)
print(json.dumps({{
    "success": True,
    "bytes_written": len(html),
    "error": None,
    "http_status": 200,
}}))
"""


FAILURE_SCRIPT = """
import json
print(json.dumps({
    "success": False,
    "bytes_written": 0,
    "error": "HTTP 403 Forbidden",
    "http_status": 403,
}))
"""


SUCCESS_NO_WRITE_SCRIPT = """
import json
print(json.dumps({
    "success": True,
    "bytes_written": 999,
    "error": None,
    "http_status": 200,
}))
"""


SUCCESS_EMPTY_WRITE_SCRIPT = """
import json
import os

html_path = os.environ[{env_key!r}]
with open(html_path, "w", encoding="utf-8") as fh:
    fh.write("")
print(json.dumps({{
    "success": True,
    "bytes_written": 0,
    "error": None,
    "http_status": 200,
}}))
"""


LEAKED_HTML_SCRIPT = """
import json
import os

html_path = os.environ[{env_key!r}]
html = "<html><body>leaked</body></html>"
with open(html_path, "w", encoding="utf-8") as fh:
    fh.write(html)
print(html)
print(json.dumps({{
    "success": True,
    "bytes_written": len(html),
    "error": None,
    "http_status": 200,
}}))
"""


def _run_execute(
    code,
    judge_return=JudgeResult(ok=True, reason="Primary content present.", cost=0.0),
):
    client = MagicMock()
    llm_calls = [0]
    with patch(
        "services.execution_service.judge_retrieval",
        return_value=judge_return,
    ):
        return execute_code(
            code,
            "test.example",
            "requests_basic",
            "http://test.example/page",
            client,
            llm_calls,
        )


class TestExecutionTransport(unittest.TestCase):
    def test_parse_status_json_single_line_ok(self):
        output = '{"success": true, "bytes_written": 10, "error": null, "http_status": 200}'
        result, err = _parse_status_json(output)
        self.assertIsNone(err)
        self.assertTrue(result["success"])
        self.assertEqual(result["bytes_written"], 10)

    def test_parse_status_json_rejects_extra_stdout_lines(self):
        output = (
            "<html><body>leaked HTML must not appear on stdout</body></html>\n"
            '{"success": true, "bytes_written": 10, "error": null, "http_status": 200}'
        )
        result, err = _parse_status_json(output)
        self.assertIsNone(result)
        self.assertIn("output contract", err)

    def test_minimal_env_excludes_parent_secrets(self):
        with patch.dict(
            os.environ,
            {"OPENROUTER_API_KEY": "secret-should-not-leak", "PATH": "/usr/bin"},
            clear=False,
        ):
            env = _minimal_subprocess_env("/tmp/out.html")
        self.assertNotIn("OPENROUTER_API_KEY", env)
        self.assertEqual(env["PATH"], "/usr/bin")
        self.assertEqual(env[settings.RETRIEVAL_HTML_PATH_ENV], "/tmp/out.html")

    def test_execute_code_reads_html_from_file(self):
        code = SUCCESS_SCRIPT.format(env_key=settings.RETRIEVAL_HTML_PATH_ENV)
        result = _run_execute(code)
        self.assertTrue(result.success, result.error)
        self.assertGreater(len(result.html), 50000)
        self.assertIn("<html>", result.html)
        self.assertEqual(result.http_status, 200)

    def test_execute_code_large_html_round_trips_via_file(self):
        code = LARGE_SUCCESS_SCRIPT.format(
            env_key=settings.RETRIEVAL_HTML_PATH_ENV,
            payload_size=LARGE_HTML_BYTES,
        )
        result = _run_execute(code)
        self.assertTrue(result.success, result.error)
        self.assertGreaterEqual(len(result.html.encode("utf-8")), LARGE_HTML_BYTES)
        self.assertEqual(result.http_status, 200)

    def test_execute_code_script_failure_plumbs_http_status(self):
        result = _run_execute(FAILURE_SCRIPT)
        self.assertFalse(result.success)
        self.assertEqual(result.html, "")
        self.assertIn("403", result.error)
        self.assertEqual(result.http_status, 403)

    def test_execute_code_success_without_file_write(self):
        result = _run_execute(SUCCESS_NO_WRITE_SCRIPT)
        self.assertFalse(result.success)
        self.assertEqual(result.html, "")
        self.assertIn("never wrote the HTML file", result.error)

    def test_execute_code_success_with_empty_file(self):
        code = SUCCESS_EMPTY_WRITE_SCRIPT.format(
            env_key=settings.RETRIEVAL_HTML_PATH_ENV
        )
        result = _run_execute(code)
        self.assertFalse(result.success)
        self.assertEqual(result.html, "")
        self.assertIn("empty HTML file", result.error)

    def test_execute_code_rejects_leaked_html_on_stdout(self):
        code = LEAKED_HTML_SCRIPT.format(env_key=settings.RETRIEVAL_HTML_PATH_ENV)
        result = _run_execute(code)
        self.assertFalse(result.success)
        self.assertEqual(result.html, "")
        self.assertIn("output contract", result.error)

    def test_execute_code_judge_unavailable_lean_accepts(self):
        code = SUCCESS_SCRIPT.format(env_key=settings.RETRIEVAL_HTML_PATH_ENV)
        result = _run_execute(
            code,
            judge_return=JudgeResult(
                ok=True,
                reason="judge unavailable",
                judge_unavailable=True,
                cost=0.0,
            ),
        )
        self.assertTrue(result.success)
        self.assertTrue(result.judge_unavailable)
        self.assertFalse(result.content_rejected)

    def test_execute_code_judge_reject_sets_content_rejected(self):
        code = SUCCESS_SCRIPT.format(env_key=settings.RETRIEVAL_HTML_PATH_ENV)
        result = _run_execute(
            code,
            judge_return=JudgeResult(
                ok=False,
                reason="JS shell with no content.",
                cost=0.01,
                content_rejected=True,
            ),
        )
        self.assertFalse(result.success)
        self.assertTrue(result.content_rejected)
        self.assertEqual(result.failure_code, "content_rejected")
        self.assertEqual(result.error, "JS shell with no content.")
        self.assertTrue(result.html)

    def test_execute_code_contract_violation_sets_failure_code(self):
        code = LEAKED_HTML_SCRIPT.format(env_key=settings.RETRIEVAL_HTML_PATH_ENV)
        result = _run_execute(code)
        self.assertFalse(result.success)
        self.assertEqual(result.failure_code, "contract_violation")

    def test_execute_code_script_reports_typed_timeout(self):
        script = """
import json
print(json.dumps({
    "success": False,
    "bytes_written": 0,
    "error": "requests timed out after 15s",
    "http_status": None,
    "failure_code": "timeout",
}))
"""


        result = _run_execute(script)
        self.assertFalse(result.success)
        self.assertEqual(result.failure_code, "timeout")
        self.assertIsNone(result.http_status)


if __name__ == "__main__":
    unittest.main()
