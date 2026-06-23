import sys
import unittest
from pathlib import Path

project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from utils.failure_code import (
    CONNECTION_ERROR,
    CONTRACT_VIOLATION,
    SCRIPT_ERROR,
    TIMEOUT,
)
from utils.retry_classifier import DETERMINISTIC, TRANSIENT, classify_retry_outcome


class TestClassifyRetryOutcome(unittest.TestCase):
    def test_429_is_transient(self):
        self.assertEqual(classify_retry_outcome(http_status=429), TRANSIENT)

    def test_5xx_is_transient(self):
        self.assertEqual(classify_retry_outcome(http_status=503), TRANSIENT)
        self.assertEqual(classify_retry_outcome(http_status=502), TRANSIENT)

    def test_403_is_deterministic(self):
        self.assertEqual(classify_retry_outcome(http_status=403), DETERMINISTIC)

    def test_401_is_deterministic(self):
        self.assertEqual(classify_retry_outcome(http_status=401), DETERMINISTIC)

    def test_null_status_timeout_code_is_transient(self):
        self.assertEqual(
            classify_retry_outcome(http_status=None, failure_code=TIMEOUT),
            TRANSIENT,
        )

    def test_null_status_connection_error_code_is_transient(self):
        self.assertEqual(
            classify_retry_outcome(http_status=None, failure_code=CONNECTION_ERROR),
            TRANSIENT,
        )

    def test_null_status_contract_violation_is_deterministic(self):
        self.assertEqual(
            classify_retry_outcome(http_status=None, failure_code=CONTRACT_VIOLATION),
            DETERMINISTIC,
        )

    def test_null_status_script_error_is_deterministic(self):
        self.assertEqual(
            classify_retry_outcome(http_status=None, failure_code=SCRIPT_ERROR),
            DETERMINISTIC,
        )

    def test_error_prose_does_not_affect_classification(self):

        self.assertEqual(
            classify_retry_outcome(
                http_status=None,
                failure_code=CONTRACT_VIOLATION,
            ),
            DETERMINISTIC,
        )
        self.assertEqual(
            classify_retry_outcome(
                http_status=None,
                failure_code=TIMEOUT,
            ),
            TRANSIENT,
        )

    def test_content_rejected_is_deterministic(self):
        self.assertEqual(
            classify_retry_outcome(
                http_status=200,
                failure_code=None,
                content_rejected=True,
            ),
            DETERMINISTIC,
        )

    def test_404_is_deterministic(self):
        self.assertEqual(classify_retry_outcome(http_status=404), DETERMINISTIC)


if __name__ == "__main__":
    unittest.main()
