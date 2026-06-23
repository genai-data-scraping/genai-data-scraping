import sys
import unittest
from pathlib import Path

project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from utils.failure_code import (
    CONNECTION_ERROR,
    SCRIPT_ERROR,
    TIMEOUT,
    normalize_script_failure_code,
)


class TestFailureCode(unittest.TestCase):
    def test_normalize_accepts_known_script_codes(self):
        self.assertEqual(normalize_script_failure_code(TIMEOUT), TIMEOUT)
        self.assertEqual(normalize_script_failure_code(CONNECTION_ERROR), CONNECTION_ERROR)

    def test_normalize_unknown_defaults_to_script_error(self):
        self.assertEqual(normalize_script_failure_code("garbage"), SCRIPT_ERROR)
        self.assertEqual(normalize_script_failure_code(None), SCRIPT_ERROR)


if __name__ == "__main__":
    unittest.main()
