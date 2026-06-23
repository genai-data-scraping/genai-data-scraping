import sys
import unittest
from pathlib import Path

project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from config import settings


class TestSettingsDefaults(unittest.TestCase):
    def test_default_mode_is_ladder(self):
        self.assertEqual(settings.DEFAULT_MODE, "ladder")

    def test_llm_model_is_sonnet_46(self):
        self.assertEqual(settings.LLM_MODEL, "anthropic/claude-sonnet-4.6")


if __name__ == "__main__":
    unittest.main()
