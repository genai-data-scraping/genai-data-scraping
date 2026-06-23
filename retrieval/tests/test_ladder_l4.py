import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

project_root = Path(__file__).resolve().parents[1]
repo_root = project_root.parent
sys.path.insert(0, str(repo_root))
sys.path.insert(0, str(project_root))

from config import settings
from services.execution_result import ExecutionResult
from services.ladder_service import run_ladder
from utils.failure_kind import JUDGE_REJECT, TRANSIENT_EXHAUSTED


def _mock_llm_generate(_client, _messages, llm_calls, level, _domain):
    llm_calls[0] += 1
    return f"# generated code for {level}\n", 0.0


class TestLadderL4Routing(unittest.TestCase):
    def setUp(self):
        self.api_key_patch = patch.object(settings, "SCRAPINGBEE_API_KEY", "test-key")
        self.api_key_patch.start()

    def tearDown(self):
        self.api_key_patch.stop()

    @patch("utils.retry_loop.sleep_before_retry")
    @patch("services.ladder_service.execute_code")
    @patch("services.ladder_service.llm_generate", side_effect=_mock_llm_generate)
    @patch("services.ladder_service.get_client")
    def test_l4_transient_exhaust_produces_all_failed(
        self, mock_get_client, _mock_gen, mock_execute, _mock_sleep
    ):

        mock_get_client.return_value = MagicMock()
        l4_calls = {"n": 0}

        def execute_side_effect(_code, _domain, level, _url, _client, _llm_calls):
            if level == "scrapingbee":
                l4_calls["n"] += 1
                return ExecutionResult(
                    success=False,
                    error="ScrapingBee HTTP 503",
                    http_status=503,
                    failure_code="http_error",
                )
            return ExecutionResult(
                success=False,
                error="HTTP 403 Forbidden",
                http_status=403,
                failure_code="http_error",
            )

        mock_execute.side_effect = execute_side_effect

        result = run_ladder("https://example.com/page", "example.com", mode="ladder")

        self.assertFalse(result["success"])
        self.assertEqual(result["level"], "all_failed")
        self.assertEqual(result["level_index"], 5)
        self.assertEqual(len(result["history"]), 4)
        self.assertEqual(result["history"][-1]["level"], "scrapingbee")
        self.assertEqual(result["history"][-1]["failure_kind"], TRANSIENT_EXHAUSTED)
        self.assertEqual(l4_calls["n"], settings.RETRY_MAX_ATTEMPTS_L4)

    @patch("services.ladder_service.execute_code")
    @patch("services.ladder_service.llm_generate", side_effect=_mock_llm_generate)
    @patch("services.ladder_service.get_client")
    def test_l4_judge_reject_produces_all_failed(
        self, mock_get_client, _mock_gen, mock_execute
    ):

        mock_get_client.return_value = MagicMock()

        def execute_side_effect(_code, _domain, level, _url, _client, _llm_calls):
            if level == "scrapingbee":
                return ExecutionResult(
                    success=False,
                    error="Empty JavaScript shell with no body content.",
                    http_status=200,
                    failure_code="content_rejected",
                    content_rejected=True,
                    html="<html><body><div id='root'></div></body></html>",
                    llm_cost_usd=0.01,
                )
            return ExecutionResult(
                success=False,
                error="HTTP 403 Forbidden",
                http_status=403,
                failure_code="http_error",
            )

        mock_execute.side_effect = execute_side_effect

        result = run_ladder("https://example.com/page", "example.com", mode="ladder")

        self.assertFalse(result["success"])
        self.assertEqual(result["level"], "all_failed")
        last = result["history"][-1]
        self.assertEqual(last["level"], "scrapingbee")
        self.assertEqual(last["failure_kind"], JUDGE_REJECT)
        self.assertIn("shell", last["error"].lower())
        self.assertEqual(mock_execute.call_count, 4)


if __name__ == "__main__":
    unittest.main()
