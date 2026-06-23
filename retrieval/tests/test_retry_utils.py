import sys
import unittest
from pathlib import Path

project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from config import settings
from utils.retry_utils import backoff_seconds, max_attempts_for_level


class TestRetryUtils(unittest.TestCase):
    def test_max_attempts_code_levels(self):
        self.assertEqual(max_attempts_for_level("requests_basic"), settings.RETRY_MAX_ATTEMPTS_CODE)
        self.assertEqual(max_attempts_for_level("playwright"), settings.RETRY_MAX_ATTEMPTS_CODE)

    def test_max_attempts_l4(self):
        self.assertEqual(max_attempts_for_level("scrapingbee"), settings.RETRY_MAX_ATTEMPTS_L4)

    def test_backoff_respects_retry_after(self):
        delay = backoff_seconds(0, "requests_basic", retry_after_seconds=10.0)
        floor = 10.0 * (1 - settings.RETRY_JITTER_FRACTION)
        self.assertGreaterEqual(delay, floor)

    def test_l4_backoff_capped(self):
        delay = backoff_seconds(10, "scrapingbee")
        self.assertLessEqual(delay, settings.RETRY_BACKOFF_MAX_SECONDS * 1.25)


if __name__ == "__main__":
    unittest.main()
