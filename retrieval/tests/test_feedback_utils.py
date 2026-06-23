import sys
import unittest
from pathlib import Path

project_root = Path(__file__).resolve().parents[1]
repo_root = project_root.parent
sys.path.insert(0, str(repo_root))
sys.path.insert(0, str(project_root))

from utils.failure_kind import FETCH_ERROR, JUDGE_REJECT, TRANSIENT_EXHAUSTED
from utils.feedback_utils import build_failure_feedback


class TestBuildFailureFeedback(unittest.TestCase):
    def test_fetch_error_with_http_status(self):
        history = [{
            "level": "requests_headers",
            "success": False,
            "failure_kind": FETCH_ERROR,
            "http_status": 403,
            "bytes_written": 0,
            "error": "Forbidden",
        }]
        feedback = build_failure_feedback(history)
        self.assertIn("HTTP 403", feedback)
        self.assertIn("L2: Requests + Headers", feedback)
        self.assertIn("Forbidden", feedback)

    def test_fetch_error_without_http_status(self):
        history = [{
            "level": "requests_basic",
            "success": False,
            "failure_kind": FETCH_ERROR,
            "http_status": None,
            "bytes_written": 0,
            "error": "Timed out after 300s",
        }]
        feedback = build_failure_feedback(history)
        self.assertIn("failed before a successful HTTP response", feedback)
        self.assertIn("Timed out after 300s", feedback)

    def test_fetch_error_with_bytes_before_judge_wires(self):

        history = [{
            "level": "requests_basic",
            "success": False,
            "failure_kind": FETCH_ERROR,
            "http_status": 200,
            "bytes_written": 8000,
            "error": "Page too small — likely JS shell or block page.",
        }]
        feedback = build_failure_feedback(history)
        self.assertIn("fetched 8,000 bytes but retrieval failed", feedback)
        self.assertNotIn("not real page content", feedback)

    def test_judge_reject_template_branch(self):

        history = [{
            "level": "playwright",
            "success": False,
            "failure_kind": JUDGE_REJECT,
            "http_status": 200,
            "bytes_written": 12000,
            "error": "Cloudflare challenge page detected.",
        }]
        feedback = build_failure_feedback(history)
        self.assertIn("not real page content", feedback)
        self.assertIn("12,000 bytes", feedback)

    def test_transient_exhausted_template_branch(self):

        history = [{
            "level": "requests_basic",
            "success": False,
            "failure_kind": TRANSIENT_EXHAUSTED,
            "http_status": None,
            "bytes_written": 0,
            "error": "HTTP 429 after 3 retries",
        }]
        feedback = build_failure_feedback(history)
        self.assertIn("repeated transient failures", feedback)

    def test_skips_successful_attempts(self):
        history = [
            {
                "level": "requests_basic",
                "success": True,
                "bytes_written": 90000,
                "http_status": 200,
            },
            {
                "level": "requests_headers",
                "success": False,
                "failure_kind": FETCH_ERROR,
                "http_status": 401,
                "bytes_written": 0,
                "error": "Unauthorized",
            },
        ]
        feedback = build_failure_feedback(history)
        self.assertNotIn("L1:", feedback)
        self.assertIn("HTTP 401", feedback)


if __name__ == "__main__":
    unittest.main()
