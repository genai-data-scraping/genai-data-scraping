import sys
import unittest
from io import StringIO
from pathlib import Path
from unittest.mock import patch

project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from services.ladder_service import write_summary


class TestWriteSummary(unittest.TestCase):
    def test_reports_unjudged_separately(self):
        results = [
            {
                "domain": "example.com",
                "success": True,
                "level_index": 1,
                "llm_cost_usd": 0.01,
                "elapsed_s": 5.0,
                "judge_unavailable": True,
            },
            {
                "domain": "example.com",
                "success": True,
                "level_index": 2,
                "llm_cost_usd": 0.02,
                "elapsed_s": 8.0,
                "judge_unavailable": False,
            },
            {
                "domain": "example.com",
                "success": False,
                "level_index": 5,
                "llm_cost_usd": 0.03,
                "elapsed_s": 12.0,
                "judge_unavailable": False,
            },
        ]

        buf = StringIO()
        with patch("builtins.print", lambda *args, **kwargs: buf.write(" ".join(map(str, args)) + "\n")):
            write_summary(results, "/tmp")

        output = buf.getvalue()
        self.assertIn("Unjd", output)
        self.assertIn("Unjudged total: 1 page(s) accepted without verdict", output)


if __name__ == "__main__":
    unittest.main()
