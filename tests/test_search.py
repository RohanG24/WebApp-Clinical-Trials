import json
import os
import unittest

from clinical_trials.burden import estimate_time_commitment
from clinical_trials.search import build_result, filter_by_level

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "sample_study.json")


def load_fixture():
    with open(FIXTURE, encoding="utf-8") as handle:
        return json.load(handle)


def protocol_with_schedule(text):
    return {"descriptionModule": {"detailedDescription": text}}


class EstimateTimeCommitmentTests(unittest.TestCase):
    def test_sample_is_moderate(self):
        # Every 3 weeks, clinic infusions, plus one overnight -> ~5 hrs/week.
        est = estimate_time_commitment(load_fixture()["protocolSection"])
        self.assertEqual(est["level"], "Moderate")
        self.assertEqual(est["rank"], 1)
        self.assertIn("hours a week", est["hours"])

    def test_daily_oral_is_light(self):
        est = estimate_time_commitment(
            protocol_with_schedule("Patients take one tablet by mouth every day at home.")
        )
        self.assertEqual(est["level"], "Light")

    def test_daily_clinic_infusion_is_intensive(self):
        est = estimate_time_commitment(
            protocol_with_schedule("Patients receive an IV infusion in the clinic every day.")
        )
        self.assertEqual(est["level"], "Intensive")

    def test_no_schedule_is_unknown(self):
        est = estimate_time_commitment(protocol_with_schedule("This study looks at outcomes."))
        self.assertEqual(est["level"], "Unknown")
        self.assertIsNone(est["hours"])
        self.assertEqual(est["rank"], 3)


class BuildResultTests(unittest.TestCase):
    def setUp(self):
        self.result = build_result(load_fixture())

    def test_core_fields(self):
        self.assertEqual(self.result["nct_id"], "NCT05773144")
        self.assertIn("Breast Cancer", self.result["title"])
        self.assertEqual(self.result["url"], "https://clinicaltrials.gov/study/NCT05773144")
        self.assertEqual(self.result["status"], "Recruiting")

    def test_conditions_and_locations(self):
        self.assertIn("Breast Cancer", self.result["conditions"])
        self.assertEqual(self.result["location_count"], 2)
        self.assertTrue(any("Boston" in loc for loc in self.result["locations"]))

    def test_includes_time_estimate(self):
        self.assertEqual(self.result["time"]["level"], "Moderate")


class FilterByLevelTests(unittest.TestCase):
    def _mk(self, level, rank):
        return {"title": "x", "time": {"level": level, "rank": rank}}

    def test_light_ceiling_excludes_intensive_keeps_unknown(self):
        rows = [
            self._mk("Light", 0),
            self._mk("Moderate", 1),
            self._mk("Intensive", 2),
            self._mk("Unknown", 3),
        ]
        kept = filter_by_level(rows, "Light")
        levels = [r["time"]["level"] for r in kept]
        self.assertIn("Light", levels)
        self.assertIn("Unknown", levels)          # cannot rule out -> kept, flagged
        self.assertNotIn("Moderate", levels)
        self.assertNotIn("Intensive", levels)

    def test_moderate_ceiling(self):
        rows = [self._mk("Light", 0), self._mk("Moderate", 1), self._mk("Intensive", 2)]
        kept = filter_by_level(rows, "Moderate")
        self.assertEqual({r["time"]["level"] for r in kept}, {"Light", "Moderate"})


if __name__ == "__main__":
    unittest.main()
