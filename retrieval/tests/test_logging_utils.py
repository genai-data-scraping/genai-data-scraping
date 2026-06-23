import sys
import unittest
from pathlib import Path
from unittest.mock import patch

project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

import utils.logging_utils as logging_utils
from utils.logging_utils import style


class TestLoggingUtils(unittest.TestCase):
    def setUp(self):
        logging_utils._color_enabled = None

    def tearDown(self):
        logging_utils._color_enabled = None

    def test_style_plain_when_not_tty(self):
        with patch.object(sys.stdout, "isatty", return_value=False):
            logging_utils._color_enabled = None
            self.assertEqual(style("hello", "success"), "hello")

    def test_style_ansi_when_tty(self):
        with patch.object(sys.stdout, "isatty", return_value=True):
            logging_utils._color_enabled = None
            out = style("hello", "success")
            self.assertIn("\033[32m", out)
            self.assertIn("hello", out)
            self.assertIn("\033[0m", out)


if __name__ == "__main__":
    unittest.main()
