import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from openai import APIConnectionError

from config import settings
from services.judge_service import (
    JudgeResult,
    _judge_sample,
    _parse_judge_response,
    judge_retrieval,
)


class TestJudgeService(unittest.TestCase):
    def test_judge_sample_bounded_slices(self):
        html = "a" * 10000
        sample = _judge_sample(html)
        self.assertIn("=== HEAD", sample)
        self.assertIn("=== MID", sample)
        self.assertLessEqual(len(sample), 10000)

    def test_parse_judge_response_valid(self):
        ok, reason = _parse_judge_response(
            '{"ok": false, "reason": "Cloudflare challenge page."}'
        )
        self.assertFalse(ok)
        self.assertEqual(reason, "Cloudflare challenge page.")

    def test_parse_judge_response_unparseable_fails_closed(self):
        ok, reason = _parse_judge_response("not json at all")
        self.assertIsNone(ok)
        self.assertEqual(reason, "judge unparseable")

    def test_empty_html_floor_no_llm(self):
        client = MagicMock()
        llm_calls = [0]
        result = judge_retrieval(client, "  ", "http://x", "x.com", llm_calls)
        self.assertFalse(result.ok)
        self.assertTrue(result.content_rejected)
        self.assertEqual(result.reason, "Empty HTML response.")
        self.assertEqual(result.cost, 0.0)
        self.assertEqual(llm_calls[0], 0)
        client.chat.completions.create.assert_not_called()

    def test_judge_reject_from_verdict_not_bytes(self):
        client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.choices = [MagicMock(message=MagicMock(
            content='{"ok": false, "reason": "JS shell with no content."}'
        ))]
        mock_resp.usage = MagicMock(prompt_tokens=100, completion_tokens=20)
        client.chat.completions.create.return_value = mock_resp

        llm_calls = [0]
        result = judge_retrieval(
            client, "<html><body>loading...</body></html>", "http://x", "x.com", llm_calls
        )
        self.assertFalse(result.ok)
        self.assertTrue(result.content_rejected)
        self.assertFalse(result.judge_unavailable)
        self.assertEqual(result.reason, "JS shell with no content.")
        self.assertEqual(llm_calls[0], 1)

    def test_unparseable_does_not_retry_or_lean_accept(self):
        client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.choices = [MagicMock(message=MagicMock(content="not json"))]
        mock_resp.usage = MagicMock(prompt_tokens=10, completion_tokens=5)
        client.chat.completions.create.return_value = mock_resp

        llm_calls = [0]
        result = judge_retrieval(
            client, "<html>body</html>", "http://x", "x.com", llm_calls
        )
        self.assertFalse(result.ok)
        self.assertTrue(result.content_rejected)
        self.assertFalse(result.judge_unavailable)
        self.assertEqual(result.reason, "judge unparseable")
        self.assertEqual(client.chat.completions.create.call_count, 1)

    def test_infra_error_retries_then_lean_accepts(self):
        client = MagicMock()
        client.chat.completions.create.side_effect = APIConnectionError(
            request=MagicMock()
        )

        llm_calls = [0]
        with patch("services.judge_service.time.sleep"):
            result = judge_retrieval(
                client, "<html>content</html>", "http://x", "x.com", llm_calls
            )

        self.assertTrue(result.ok)
        self.assertTrue(result.judge_unavailable)
        self.assertFalse(result.content_rejected)
        self.assertEqual(
            client.chat.completions.create.call_count,
            settings.JUDGE_MAX_ATTEMPTS,
        )

    def test_infra_error_recovers_on_second_attempt(self):
        client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.choices = [MagicMock(message=MagicMock(
            content='{"ok": true, "reason": "Article body present."}'
        ))]
        mock_resp.usage = MagicMock(prompt_tokens=10, completion_tokens=5)
        client.chat.completions.create.side_effect = [
            APIConnectionError(request=MagicMock()),
            mock_resp,
        ]

        llm_calls = [0]
        with patch("services.judge_service.time.sleep"):
            result = judge_retrieval(
                client, "<html>content</html>", "http://x", "x.com", llm_calls
            )

        self.assertTrue(result.ok)
        self.assertFalse(result.judge_unavailable)
        self.assertEqual(result.reason, "Article body present.")
        self.assertEqual(client.chat.completions.create.call_count, 2)


if __name__ == "__main__":
    unittest.main()
