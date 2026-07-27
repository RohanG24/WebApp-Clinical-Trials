import json
import os
import unittest

from clinical_trials.burden import assess_side_effects, assess_time_toxicity

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "sample_study.json")


def load_fixture():
    with open(FIXTURE, encoding="utf-8") as handle:
        return json.load(handle)


def strip_bold(text):
    return text.replace("[[b]]", "").replace("[[/b]]", "")


class TimeToxicityTests(unittest.TestCase):
    def setUp(self):
        self.data = load_fixture()
        self.section = assess_time_toxicity(self.data["protocolSection"])
        self.raw = "\n".join(self.section["bullets"])
        self.text = strip_bold(self.raw)

    def test_duration_and_cadence_are_bolded(self):
        self.assertIn("[[b]]2 years 6 months[[/b]]", self.raw)
        self.assertIn("[[b]]about every 3 weeks[[/b]]", self.raw)
        self.assertIn("[[b]]21-day cycles[[/b]]", self.raw)

    def test_section_is_featured(self):
        self.assertTrue(self.section["featured"])
        self.assertIn("time", self.section["heading"].lower())

    def test_overall_duration_estimated(self):
        # June 2023 -> Dec 2025 is about 2 years 6 months.
        self.assertIn("2 years 6 months", self.text)

    def test_dosing_cadence_extracted(self):
        self.assertIn("every 3 weeks", self.text)

    def test_cycle_length_extracted(self):
        self.assertIn("21-day cycles", self.text)

    def test_visit_and_overnight_mentions(self):
        lowered = self.text.lower()
        self.assertIn("study visit", lowered)
        self.assertIn("overnight", lowered)

    def test_confirmation_note_present(self):
        self.assertIn("confirm the exact visit schedule", self.text)


class TimeToxicityFallbackTests(unittest.TestCase):
    def test_missing_schedule_prompts_to_ask(self):
        protocol = {"identificationModule": {"nctId": "NCT00000000"}}
        section = assess_time_toxicity(protocol)
        text = "\n".join(section["bullets"])
        self.assertIn("ask the study team", text.lower())


class SideEffectTests(unittest.TestCase):
    def setUp(self):
        self.data = load_fixture()
        self.section = assess_side_effects(self.data)
        self.raw = "\n".join(self.section["bullets"])
        self.text = strip_bold(self.raw)

    def test_percentages_are_bolded(self):
        self.assertIn("[[b]]33%[[/b]]", self.raw)

    def test_section_is_featured(self):
        self.assertTrue(self.section["featured"])

    def test_common_effects_aggregated_across_arms(self):
        # Nausea: (45+20)/(100+100) = 32.5% -> ~33%
        self.assertIn("Nausea", self.text)
        self.assertIn("33%", self.text)

    def test_common_effects_sorted_most_frequent_first(self):
        # Nausea (~33%) should appear before Fatigue (~28%).
        self.assertLess(self.text.index("Nausea"), self.text.index("Fatigue"))

    def test_serious_effects_listed(self):
        self.assertIn("Febrile neutropenia", self.text)


class SideEffectFallbackTests(unittest.TestCase):
    def test_no_results_section_says_not_posted(self):
        data = {
            "protocolSection": {
                "armsInterventionsModule": {
                    "interventions": [{"type": "DRUG", "name": "Drug Y"}]
                }
            }
        }
        section = assess_side_effects(data)
        text = "\n".join(section["bullets"])
        self.assertIn("not been posted", text)
        self.assertIn("Drug Y", text)


if __name__ == "__main__":
    unittest.main()
