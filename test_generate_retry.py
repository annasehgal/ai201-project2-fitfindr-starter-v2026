"""
Controlled test of the 5xx retry in generate.py (unit 4, Milestone 5).

    python test_generate_retry.py

No network and no API key: the model client is replaced with a fake that
raises or answers in a fixed order, and time.sleep is replaced so backoff
waits cost nothing. The errors are the real google-genai exception classes,
built the same way the client builds them for an HTTP error.
"""

import contextlib
import io
import unittest
from types import SimpleNamespace
from unittest import mock

from google.genai import errors

import config
import generate
from generate import ModelUnavailable


def server_error(code=503, status="UNAVAILABLE"):
    return errors.ServerError(code, {"error": {
        "code": code,
        "message": "This model is currently experiencing high demand. "
                   "Spikes in demand are usually temporary. Please try again later.",
        "status": status,
    }})


def client_error(code, message, status):
    return errors.ClientError(code, {"error": {
        "code": code, "message": message, "status": status,
    }})


def ok(text="a fit card"):
    return SimpleNamespace(text=text, usage_metadata=None)


class RetryTest(unittest.TestCase):

    def setUp(self):
        generate._call_times.clear()
        generate._session_calls = 0
        self.calls = mock.Mock()
        fake_client = SimpleNamespace(models=SimpleNamespace(generate_content=self.calls))
        self.stderr = io.StringIO()
        patches = [
            mock.patch.object(generate, "_get_client", return_value=fake_client),
            mock.patch.object(generate.time, "sleep"),
            mock.patch("random.uniform", return_value=0.5),
            mock.patch.object(config, "CACHE_ENABLED", False),
            contextlib.redirect_stderr(self.stderr),
        ]
        for p in patches:
            p.__enter__()
            self.addCleanup(p.__exit__, None, None, None)
        self.sleep = generate.time.sleep

    def test_503_then_success_is_retried(self):
        self.calls.side_effect = [server_error(), ok("caption")]
        self.assertEqual(generate.generate("p"), "caption")
        self.assertEqual(self.calls.call_count, 2)
        self.sleep.assert_called_once_with(2.5)          # 2**1 + jitter 0.5
        self.assertIn("[server busy]", self.stderr.getvalue())

    def test_two_503s_then_success_on_last_attempt(self):
        self.calls.side_effect = [server_error(), server_error(), ok("caption")]
        self.assertEqual(generate.generate("p"), "caption")
        self.assertEqual(self.calls.call_count, 3)
        self.assertEqual([c.args[0] for c in self.sleep.call_args_list], [2.5, 4.5])

    def test_repeated_503_stops_after_max_attempts(self):
        self.calls.side_effect = [server_error()] * 10
        with self.assertRaises(ModelUnavailable) as caught:
            generate.generate("p")
        self.assertEqual(self.calls.call_count, 3)   # _SERVER_BUSY_RETRIES
        self.assertEqual(self.sleep.call_count, 2)
        self.assertIn("overloaded", str(caught.exception))
        self.assertIn("3 tries", str(caught.exception))

    def test_other_5xx_codes_are_retried(self):
        for code, status in [(500, "INTERNAL"), (502, "BAD_GATEWAY"), (504, "DEADLINE_EXCEEDED")]:
            with self.subTest(code=code):
                self.calls.reset_mock()
                self.calls.side_effect = [server_error(code, status), ok()]
                self.assertEqual(generate.generate("p"), "a fit card")
                self.assertEqual(self.calls.call_count, 2)

    def test_bad_key_is_not_retried(self):
        self.calls.side_effect = [client_error(
            400, "API key not valid. Please pass a valid API key.", "INVALID_ARGUMENT")]
        with self.assertRaises(ModelUnavailable) as caught:
            generate.generate("p")
        self.assertEqual(self.calls.call_count, 1)
        self.sleep.assert_not_called()
        self.assertIn("rejected your API key", str(caught.exception))

    def test_unknown_model_is_not_retried(self):
        self.calls.side_effect = [client_error(404, "models/nope is not found.", "NOT_FOUND")]
        with self.assertRaises(ModelUnavailable):
            generate.generate("p")
        self.assertEqual(self.calls.call_count, 1)
        self.sleep.assert_not_called()

    def test_rate_limit_still_uses_its_own_retry(self):
        self.calls.side_effect = [client_error(
            429, "Resource has been exhausted. Please retry in 3s.", "RESOURCE_EXHAUSTED"), ok()]
        self.assertEqual(generate.generate("p"), "a fit card")
        self.assertEqual(self.calls.call_count, 2)
        self.assertNotIn("[server busy]", self.stderr.getvalue())

    def test_agent_handles_exhausted_retries(self):
        """Three 503s inside suggest_outfit end the run with a message, not a crash."""
        from agent import run_agent
        from utils.data_loader import get_example_wardrobe

        self.calls.side_effect = [server_error()] * 10
        with contextlib.redirect_stdout(io.StringIO()):   # keep the trace out of the test report
            session = run_agent("vintage graphic tee under $30", get_example_wardrobe())
        self.assertEqual(self.calls.call_count, 3)
        self.assertIsNone(session["fit_card"])
        self.assertEqual(session["selected_item"]["id"], "lst_002")
        self.assertIn("couldn't be reached", session["error"])
        self.assertIn("overloaded", session["error"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
