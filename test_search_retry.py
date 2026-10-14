"""
Tests for the unit 4 stretch feature: an empty search that had a size is
retried once, over MCP, without the size filter.

    python test_search_retry.py

No model calls: suggest_outfit and create_fit_card are replaced with stubs.
The unit tests also replace the MCP call with a recorder. The last two tests
use the real MCP server and the real listings data.
"""

import contextlib
import io
import unittest
from unittest import mock

import agent
from utils.data_loader import get_example_wardrobe

LISTING = {
    "id": "lst_test", "title": "Test Tee", "description": "a tee", "category": "tops",
    "style_tags": [], "size": "M", "condition": "good", "price": 20.0,
    "colors": [], "brand": None, "platform": "depop",
}


class SizeRetryTest(unittest.TestCase):

    def setUp(self):
        self.calls = []
        self.responses = []

        def fake_call_tool(name, arguments):
            self.calls.append((name, dict(arguments)))
            return self.responses.pop(0)

        self.suggest = mock.Mock(return_value="an outfit")
        self.card = mock.Mock(return_value="a fit card")
        patches = [
            mock.patch.object(agent, "call_tool", side_effect=fake_call_tool),
            # Any direct call would bypass MCP, so make one fail loudly.
            mock.patch.object(agent, "search_listings",
                              side_effect=AssertionError("direct search_listings call")),
            mock.patch.object(agent, "suggest_outfit", self.suggest),
            mock.patch.object(agent, "create_fit_card", self.card),
            contextlib.redirect_stdout(io.StringIO()),
        ]
        for p in patches:
            p.__enter__()
            self.addCleanup(p.__exit__, None, None, None)

    def run_query(self, query):
        return agent.run_agent(query, get_example_wardrobe())

    def test_retry_finds_results(self):
        self.responses = [[], [LISTING]]
        session = self.run_query("graphic tee size XL under $30")

        self.assertEqual(len(self.calls), 2)
        self.assertEqual(self.calls[0][1]["size"], "XL")
        self.assertIsNone(self.calls[1][1]["size"])
        self.assertIsNone(session["error"])
        self.assertEqual(session["selected_item"]["id"], "lst_test")
        self.assertEqual(session["size_retry"], {"dropped_size": "XL", "matches": 1})
        self.assertIn("without the size filter", session["notice"])
        self.assertIn("may not come in size XL", session["notice"])
        self.suggest.assert_called_once()
        self.assertEqual(session["fit_card"], "a fit card")

    def test_retry_also_empty_stops_before_suggest_outfit(self):
        self.responses = [[], []]
        session = self.run_query("designer ballgown size XXS under $5")

        self.assertEqual(len(self.calls), 2)            # one retry, no more
        self.suggest.assert_not_called()
        self.card.assert_not_called()
        self.assertIsNone(session["selected_item"])
        self.assertIn("without the size filter", session["notice"])
        self.assertIn("found nothing either", session["notice"])
        self.assertIn("Things to change", session["error"])
        self.assertNotIn("drop the size", session["error"])  # already dropped

    def test_retry_keeps_description_and_max_price(self):
        self.responses = [[], []]
        self.run_query("silk slip dress size L under $40")

        first, second = self.calls[0][1], self.calls[1][1]
        self.assertEqual(second["description"], first["description"])
        self.assertEqual(first["max_price"], 40.0)
        self.assertEqual(second["max_price"], 40.0)
        self.assertEqual(first["size"], "L")
        self.assertIsNone(second["size"])

    def test_no_retry_without_a_size(self):
        self.responses = [[]]
        session = self.run_query("designer ballgown under $5")

        self.assertEqual(len(self.calls), 1)
        self.assertIsNone(session["size_retry"])
        self.assertIsNone(session["notice"])
        self.assertIn("Things to change", session["error"])

    def test_no_retry_when_first_search_finds_something(self):
        self.responses = [[LISTING]]
        session = self.run_query("graphic tee size M")

        self.assertEqual(len(self.calls), 1)
        self.assertIsNone(session["size_retry"])
        self.assertIsNone(session["notice"])

    def test_both_searches_go_through_mcp(self):
        self.responses = [[], [LISTING]]
        self.run_query("graphic tee size XL")

        self.assertEqual([name for name, _ in self.calls],
                         ["search_listings", "search_listings"])
        agent.search_listings.assert_not_called()


class SizeRetryRealMCPTest(unittest.TestCase):
    """The real MCP server and the real data. Model tools are still stubbed."""

    def setUp(self):
        import mcp_client

        self.calls = []

        def recording_call_tool(name, arguments):
            self.calls.append((name, dict(arguments)))
            return mcp_client.call_tool(name, arguments)

        patches = [
            mock.patch.object(agent, "call_tool", side_effect=recording_call_tool),
            mock.patch.object(agent, "search_listings",
                              side_effect=AssertionError("direct search_listings call")),
            mock.patch.object(agent, "suggest_outfit", return_value="an outfit"),
            mock.patch.object(agent, "create_fit_card", return_value="a fit card"),
            contextlib.redirect_stdout(io.StringIO()),
        ]
        for p in patches:
            p.__enter__()
            self.addCleanup(p.__exit__, None, None, None)

    def test_real_data_size_xl_retries_and_finds(self):
        session = agent.run_agent("graphic tee size XL", get_example_wardrobe())
        self.assertEqual(len(self.calls), 2)
        self.assertEqual(session["size_retry"], {"dropped_size": "XL", "matches": 6})
        self.assertIsNotNone(session["selected_item"])
        self.assertIsNone(session["error"])

    def test_real_data_impossible_query_retries_once_then_stops(self):
        session = agent.run_agent("designer ballgown size XXS under $5", get_example_wardrobe())
        self.assertEqual(len(self.calls), 2)
        self.assertEqual(self.calls[1][1],
                         {"description": "designer ballgown", "size": None, "max_price": 5.0})
        self.assertIsNone(session["selected_item"])
        self.assertIn("found nothing either", session["notice"])


class SizeRetryCLIOutputTest(unittest.TestCase):
    """What the user actually sees from `python app.py ask '...'` (app._ask_one).

    Real MCP server and real data. Model tools are stubbed.
    """

    def setUp(self):
        self.suggest = mock.Mock(return_value="an outfit")
        patches = [
            mock.patch.object(agent, "suggest_outfit", self.suggest),
            mock.patch.object(agent, "create_fit_card", return_value="a fit card"),
        ]
        for p in patches:
            p.__enter__()
            self.addCleanup(p.__exit__, None, None, None)

    def ask(self, query):
        import app

        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            app._ask_one(query, get_example_wardrobe(), use_trace=False)
        return out.getvalue()

    def test_failed_retry_output(self):
        out = self.ask("designer ballgown size XXS under $5")
        # The dropped filter and the empty result are both stated.
        self.assertIn("Note:     Nothing matched in size XXS, so I searched again "
                      "without the size filter. That found nothing either.", out)
        # The recovery guidance is still there, minus the size it already dropped.
        self.assertIn("Things to change: try broader words", out)
        self.assertIn("raise the price ceiling above $5", out)
        self.assertNotIn("drop the size", out)
        self.assertNotIn("Found:", out)
        self.suggest.assert_not_called()
        # Notice first, then the guidance.
        self.assertLess(out.index("Note:"), out.index("Things to change"))

    def test_successful_retry_output(self):
        out = self.ask("graphic tee size XL")
        self.assertIn("Note:     Nothing matched in size XL, so I searched again "
                      "without the size filter. That found 6 listing(s), but they "
                      "may not come in size XL.", out)
        self.assertIn("Found:", out)
        self.assertLess(out.index("Note:"), out.index("Found:"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
