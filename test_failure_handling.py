"""
Tests for the capstone failure-handling layer (Shape B).

    python test_failure_handling.py

No model calls and no API key: the MCP call and the two model tools are
replaced with fakes that answer or raise on demand, and the run log is pointed
at a temporary file so these tests never write into logs/runs.jsonl.
"""

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import agent
import serve
from generate import ModelUnavailable
from mcp_client import MCPError

LISTING = {
    "id": "lst_test", "title": "Test Tee", "description": "a tee", "category": "tops",
    "style_tags": [], "size": "M", "condition": "good", "price": 20.0,
    "colors": [], "brand": None, "platform": "depop",
}


class FailureLayerTest(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.log = Path(self.tmp.name) / "runs.jsonl"
        self.client = serve.app.test_client()
        self.search = mock.Mock(return_value=[LISTING])
        self.suggest = mock.Mock(return_value="an outfit")
        self.card = mock.Mock(return_value="a fit card")
        patches = [
            mock.patch.object(serve, "LOG_FILE", self.log),
            mock.patch.object(agent, "call_tool", self.search),
            mock.patch.object(agent, "suggest_outfit", self.suggest),
            mock.patch.object(agent, "create_fit_card", self.card),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        self.addCleanup(self.tmp.cleanup)

    def ask(self, **kwargs):
        with contextlib.redirect_stdout(io.StringIO()):
            return self.client.post("/ask", **kwargs)

    def records(self):
        return [json.loads(line) for line in self.log.read_text().splitlines()]

    # ── bad input is rejected at the boundary ────────────────────────────────

    def test_malformed_bodies_get_json_400_and_a_log_record(self):
        bad = [
            dict(json={}),
            dict(json={"query": ""}),
            dict(json={"query": "   "}),
            dict(json={"query": None}),
            dict(json={"query": 123}),
            dict(json=["a"]),
            dict(data="not json", content_type="application/json"),
        ]
        for kwargs in bad:
            with self.subTest(body=kwargs):
                resp = self.ask(**kwargs)
                self.assertEqual(resp.status_code, 400)
                body = resp.get_json()
                self.assertEqual(body["error_type"], "validation_error")
                self.assertEqual(body["stage"], "validate_request")
        self.assertEqual(len(self.records()), len(bad))
        self.assertTrue(all(r["status"] == "rejected" for r in self.records()))
        self.search.assert_not_called()  # the agent never ran

    # ── downstream failures become structured responses ──────────────────────

    def test_mcp_failure_is_a_502_tool_error_at_search(self):
        self.search.side_effect = MCPError("Couldn't call 'search_listings' over MCP: boom")
        resp = self.ask(json={"query": "graphic tee"})
        self.assertEqual(resp.status_code, 502)
        body = resp.get_json()
        self.assertEqual(body["error_type"], "tool_error")
        self.assertEqual(body["stage"], "search_listings")
        self.suggest.assert_not_called()
        self.assertEqual(self.records()[-1]["error_type"], "tool_error")

    def test_model_failure_is_a_502_model_error_at_its_stage(self):
        self.suggest.side_effect = ModelUnavailable("bad key")
        resp = self.ask(json={"query": "graphic tee"})
        self.assertEqual(resp.status_code, 502)
        body = resp.get_json()
        self.assertEqual(body["error_type"], "model_error")
        self.assertEqual(body["stage"], "suggest_outfit")
        self.assertEqual(len(body["search_results"]), 1)  # search work kept

    def test_unexpected_exception_is_a_json_500_with_its_stage(self):
        self.card.side_effect = KeyError("price")
        resp = self.ask(json={"query": "graphic tee"})
        self.assertEqual(resp.status_code, 500)
        self.assertTrue(resp.is_json)
        body = resp.get_json()
        self.assertEqual(body["error_type"], "internal_error")
        self.assertEqual(body["stage"], "create_fit_card")
        self.assertEqual(self.records()[-1]["status"], "error")

    # ── "found nothing" is not a system error ────────────────────────────────

    def test_empty_search_is_no_results_not_an_error(self):
        self.search.return_value = []
        resp = self.ask(json={"query": "designer ballgown under $5"})
        self.assertEqual(resp.status_code, 200)
        body = resp.get_json()
        self.assertEqual(body["error_type"], "no_results")
        self.assertIn("Things to change", body["error"])
        self.assertEqual(self.records()[-1]["status"], "no_results")

    def test_success_is_ok_with_stage_done(self):
        resp = self.ask(json={"query": "graphic tee"})
        self.assertEqual(resp.status_code, 200)
        body = resp.get_json()
        self.assertIsNone(body["error_type"])
        self.assertEqual(body["stage"], "done")
        self.assertEqual(self.records()[-1]["status"], "ok")


    # ── the request id ties a response to its log line ───────────────────────

    def test_request_id_is_returned_and_logged(self):
        for kwargs in (dict(json={"query": "graphic tee"}), dict(json={"query": 123})):
            with self.subTest(body=kwargs):
                resp = self.ask(**kwargs)
                rid = resp.get_json()["request_id"]
                self.assertRegex(rid, r"^[0-9a-f]{12}$")
                self.assertEqual(resp.headers["X-Request-ID"], rid)
                record = self.records()[-1]
                self.assertEqual(record["request_id"], rid)
                self.assertIsInstance(record["duration_ms"], int)
        ids = [r["request_id"] for r in self.records()]
        self.assertEqual(len(ids), len(set(ids)))  # one id per request


if __name__ == "__main__":
    unittest.main(verbosity=2)
