import unittest
from types import SimpleNamespace
from unittest.mock import patch

from backend.triage import (
    TriageResult,
    analyze_report,
    contains_targeted_pii,
    detect_language,
    find_duplicate,
    normalize_message,
)


class TriageTests(unittest.TestCase):
    def setUp(self):
        self.settings = SimpleNamespace(ai_api_key="")

    def test_detects_supported_languages_and_code_switching(self):
        self.assertEqual(detect_language("The water is near the market"), "english")
        self.assertEqual(detect_language("Kuna shida ya maji kwa soko"), "swahili")
        self.assertEqual(detect_language("Wasee the water queue iko kwa soko"), "sheng")

    def test_expands_common_sms_shorthand_without_changing_other_words(self):
        self.assertEqual(
            normalize_message("  pls u check this w/ ppl  "),
            "please you check this with people",
        )

    def test_private_pii_detection_covers_named_allegations_and_contact_details(self):
        self.assertTrue(contains_targeted_pii("John stole money from the market"))
        self.assertTrue(contains_targeted_pii("Call Jane at +254 712 345 678"))
        self.assertFalse(contains_targeted_pii("There is a dispute about the market stall"))

    def test_pii_reports_are_flagged_without_a_category(self):
        result = analyze_report("John stole money from the market", self.settings)
        self.assertTrue(result.pii_flagged)
        self.assertIsNone(result.category)
        self.assertTrue(result.needs_human_review)

    def test_sheng_is_sent_to_a_human_without_local_auto_classification(self):
        result = analyze_report("Wasee the water queue iko kwa soko", self.settings)
        self.assertEqual(result.language, "sheng")
        self.assertIsNone(result.category)
        self.assertTrue(result.needs_human_review)

    def test_english_incident_is_classified_with_a_draft_summary(self):
        result = analyze_report("There is a fire near the market.", self.settings)
        self.assertEqual(result.category, "incident")
        self.assertEqual(result.summary, "There is a fire near the market.")
        self.assertFalse(result.needs_human_review)

    def test_low_confidence_sheng_ai_result_is_not_auto_categorized(self):
        ai_result = TriageResult(
            language="sheng",
            normalized_text="Wasee the water queue iko kwa soko",
            category="dispute",
            confidence=0.7,
            dispute_category="water_queues",
            summary="A reported disagreement about a water queue.",
            needs_human_review=False,
            review_reason=None,
            pii_flagged=False,
        )
        with patch("backend.triage._analyze_with_ai", return_value=ai_result):
            result = analyze_report(
                "Wasee the water queue iko kwa soko",
                SimpleNamespace(ai_api_key="configured"),
            )
        self.assertIsNone(result.category)
        self.assertIsNone(result.dispute_category)
        self.assertTrue(result.needs_human_review)

    def test_duplicate_reports_link_to_the_existing_canonical_report(self):
        duplicate = find_duplicate(
            "Fire near the market, residents are moving away.",
            [
                {
                    "id": "existing",
                    "ai_normalized_text": "Fire near the market, residents are moving away.",
                    "ai_duplicate_of": None,
                }
            ],
        )
        self.assertEqual(duplicate, "existing")


if __name__ == "__main__":
    unittest.main()
