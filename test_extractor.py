from __future__ import annotations

import unittest
from unittest.mock import patch

import requests

from spa_auditor.auditor import SpaAuditor
from spa_auditor.extractor import discover_internal_links, extract_page, summarize_pages
from spa_auditor.llm import pending_judgment
from spa_auditor.reporting import build_markdown


HTML = """
<!doctype html><html><head><title>Harbour Calm Spa</title>
<meta name="description" content="Massage and facials in Harbour Town.">
<meta name="viewport" content="width=device-width, initial-scale=1"></head><body>
<header><nav><a href="/treatments">Treatments</a><a href="/contact">Contact</a></nav></header>
<h1>Relax and restore</h1><h2>Frequently asked questions</h2>
<a class="button" href="/book">Book now</a><a href="https://instagram.com/harbourcalm">Instagram</a>
<p>Call +1 555 010 2222</p><form><input type="email"><textarea></textarea></form>
<img src="calm.jpg" alt="Massage room"><img src="team.jpg" alt="">
<script type="application/ld+json">{\"@type\": \"LocalBusiness\"}</script>
</body></html>
"""


class ExtractionTests(unittest.TestCase):
    def test_extracts_expected_spa_signals(self) -> None:
        facts = extract_page("https://spa.example/", HTML)
        self.assertEqual(facts["title"], "Harbour Calm Spa")
        self.assertTrue(facts["has_viewport_meta"])
        self.assertEqual(facts["contact_form_count"], 1)
        self.assertIn("Book now", facts["booking_cta_texts"])
        self.assertEqual(facts["alt_coverage_percent"], 50.0)
        self.assertTrue(facts["faq_hint_detected"])

    def test_discovers_only_same_host_links(self) -> None:
        links = discover_internal_links("https://spa.example/", HTML + '<a href="https://other.example/">Other</a><a href="hello@spa.example">Email</a>', 4)
        self.assertEqual(links, ["https://spa.example/treatments", "https://spa.example/contact", "https://spa.example/book"])

    def test_does_not_treat_facebook_or_faq_question_as_booking_cta(self) -> None:
        page = extract_page("https://spa.example/", """
            <a href="https://facebook.com/spa">Like on Facebook</a>
            <a href="/faq">How can I book a consultation?</a>
            <a class="btn" href="/book">Book now</a>
        """)
        self.assertEqual(page["social_links"], ["facebook.com"])
        self.assertEqual(page["booking_cta_texts"], ["Book now"])

    def test_failure_is_reported_without_a_score(self) -> None:
        facts = summarize_pages([], "https://blocked.example/", [], [{"url": "https://blocked.example/", "reason": "Timeout"}], None, "robots.txt unavailable")
        record = {
            "name": "Blocked training target",
            "url": "https://blocked.example/",
            "authorization": "own_site",
            "automatically_detected_facts": facts,
            "ai_judgment": pending_judgment("LLM review was not requested."),
        }
        report = build_markdown([record])
        self.assertIn("Graceful-failure log", report)
        self.assertIn("Timeout", report)
        self.assertIn("Awaiting LLM", report)

    def test_network_timeout_becomes_a_fact_not_a_crash(self) -> None:
        auditor = SpaAuditor(max_pages=2, delay_seconds=0, timeout_seconds=0.01)
        with patch.object(auditor.session, "get", side_effect=requests.Timeout):
            result = auditor.audit_site({
                "name": "Timeout target",
                "url": "https://timeout.example/",
                "authorization": "own_site",
            })
        failures = result.facts["audit_scope"]["failed_requests"]
        self.assertEqual(result.facts["audit_scope"]["pages_loaded"], 0)
        self.assertEqual(failures[0]["reason"], "Timeout")


if __name__ == "__main__":
    unittest.main()
