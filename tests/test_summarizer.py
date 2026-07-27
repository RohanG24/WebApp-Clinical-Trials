import json
import os
import unittest

from clinical_trials.summarizer import summarize_study

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "sample_study.json")


def load_fixture():
    with open(FIXTURE, encoding="utf-8") as handle:
        return json.load(handle)


class SummarizeStudyTests(unittest.TestCase):
    def setUp(self):
        self.summary = summarize_study(load_fixture())

    def _section(self, heading):
        for section in self.summary["sections"]:
            if section["heading"] == heading:
                return section
        self.fail(f"Missing section: {heading}")

    def test_basic_metadata(self):
        self.assertEqual(self.summary["nct_id"], "NCT05773144")
        self.assertIn("Breast Cancer", self.summary["title"])
        self.assertEqual(
            self.summary["url"], "https://clinicaltrials.gov/study/NCT05773144"
        )

    def test_relevance_detects_breast(self):
        self.assertTrue(self.summary["relevance"]["is_breast_or_colon"])
        self.assertIn("breast", self.summary["relevance"]["matched"])

    def test_overview_has_condition_and_summary(self):
        bullets = self._section("What is this study about?")["bullets"]
        self.assertTrue(any("Condition(s) studied" in b for b in bullets))
        self.assertTrue(any("Drug X" in b for b in bullets))

    def test_phase_is_plain_language(self):
        bullets = self._section("Study type and phase")["bullets"]
        self.assertTrue(any("Phase 2" in b for b in bullets))
        self.assertTrue(any("120 patients" in b for b in bullets))

    def test_status_is_plain_language(self):
        bullets = self._section("Is it enrolling now?")["bullets"]
        self.assertTrue(any("enrolling" in b.lower() for b in bullets))
        self.assertTrue(any("June" in b for b in bullets))

    def test_eligibility_parses_inclusion_and_exclusion(self):
        bullets = self._section("Who can join?")["bullets"]
        joined = "\n".join(bullets)
        self.assertIn("Female patients only", joined)
        self.assertIn("Ages 18 Years and older", joined)
        self.assertIn("You may be able to join if:", joined)
        self.assertIn("HER2-positive breast cancer", joined)
        self.assertIn("You may NOT be able to join if:", joined)
        self.assertIn("Pregnant", joined)

    def test_locations_listed(self):
        bullets = self._section("Where is it happening?")["bullets"]
        self.assertTrue(any("2 location" in b for b in bullets))
        self.assertTrue(any("Boston" in b for b in bullets))

    def test_contacts_listed(self):
        bullets = self._section("Who to contact")["bullets"]
        self.assertTrue(any("trials@example.org" in b for b in bullets))


class RelevanceWarningTests(unittest.TestCase):
    def test_non_target_condition_warns(self):
        data = {
            "protocolSection": {
                "identificationModule": {"nctId": "NCT00000000", "briefTitle": "Lung study"},
                "conditionsModule": {"conditions": ["Lung Cancer"]},
            }
        }
        summary = summarize_study(data)
        self.assertFalse(summary["relevance"]["is_breast_or_colon"])
        self.assertIn("does not clearly mention", summary["relevance"]["note"])

    def test_colorectal_detected_as_colon(self):
        data = {
            "protocolSection": {
                "identificationModule": {"nctId": "NCT00000001", "briefTitle": "CRC study"},
                "conditionsModule": {"conditions": ["Colorectal Cancer"]},
            }
        }
        summary = summarize_study(data)
        self.assertIn("colon", summary["relevance"]["matched"])


class EmptyDataTests(unittest.TestCase):
    def test_minimal_record_does_not_crash(self):
        summary = summarize_study({"protocolSection": {}})
        self.assertEqual(summary["title"], "Untitled study")
        self.assertIsInstance(summary["sections"], list)


if __name__ == "__main__":
    unittest.main()
