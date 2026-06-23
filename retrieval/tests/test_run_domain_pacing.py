import sys
import unittest
from pathlib import Path
from unittest.mock import patch

project_root = Path(__file__).resolve().parents[1]
repo_root = project_root.parent
sys.path.insert(0, str(repo_root))
sys.path.insert(0, str(project_root))

from config import settings
from services.ladder_service import run_domain


class TestRunDomainPacing(unittest.TestCase):
    @patch("services.ladder_service.run_ladder")
    @patch("services.ladder_service.time.sleep")
    def test_paces_between_urls_not_before_first(self, mock_sleep, mock_ladder):
        mock_ladder.return_value = {"success": True}
        urls = ["https://a.example/1", "https://a.example/2", "https://a.example/3"]

        with patch.object(settings, "INTER_URL_DELAY_SECONDS", 2.0):
            results = run_domain("example.com", urls)

        self.assertEqual(len(results), 3)
        self.assertEqual(mock_sleep.call_count, 2)
        mock_sleep.assert_called_with(2.0)

    @patch("services.ladder_service.run_ladder")
    @patch("services.ladder_service.time.sleep")
    def test_zero_delay_skips_sleep(self, mock_sleep, mock_ladder):
        mock_ladder.return_value = {"success": True}
        urls = ["https://a.example/1", "https://a.example/2"]

        with patch.object(settings, "INTER_URL_DELAY_SECONDS", 0):
            run_domain("example.com", urls)

        mock_sleep.assert_not_called()


if __name__ == "__main__":
    unittest.main()
