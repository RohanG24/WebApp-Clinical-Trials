import unittest

from clinical_trials.fetcher import normalize_nct_id, TrialFetchError


class NormalizeNctIdTests(unittest.TestCase):
    def test_already_canonical(self):
        self.assertEqual(normalize_nct_id("NCT05773144"), "NCT05773144")

    def test_lowercase_and_spaces(self):
        self.assertEqual(normalize_nct_id("  nct05773144 "), "NCT05773144")

    def test_bare_eight_digits(self):
        self.assertEqual(normalize_nct_id("05773144"), "NCT05773144")

    def test_full_url(self):
        self.assertEqual(
            normalize_nct_id("https://clinicaltrials.gov/study/NCT05773144"),
            "NCT05773144",
        )

    def test_empty_raises(self):
        with self.assertRaises(TrialFetchError):
            normalize_nct_id("")

    def test_wrong_digit_count_raises(self):
        with self.assertRaises(TrialFetchError):
            normalize_nct_id("NCT123")

    def test_garbage_raises(self):
        with self.assertRaises(TrialFetchError):
            normalize_nct_id("not-a-trial")


if __name__ == "__main__":
    unittest.main()
