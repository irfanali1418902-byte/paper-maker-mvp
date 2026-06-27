"""Unit tests for item_analysis_service Phase A — pure functions, no DB.

Phase A covers expected difficulty from Bloom level, stored-vs-expected
mismatch detection, and the paper balance summary.
"""

from app.services.item_analysis_service import (
    expected_difficulty,
    is_difficulty_mismatch,
    summarize_paper_balance,
)

# ---- expected_difficulty ----------------------------------------------------


class TestExpectedDifficulty:

    def test_remember_and_understand_are_easy(self):
        assert expected_difficulty("REMEMBER") == "Easy"
        assert expected_difficulty("UNDERSTAND") == "Easy"

    def test_apply_and_analyze_are_medium(self):
        assert expected_difficulty("APPLY") == "Medium"
        assert expected_difficulty("ANALYZE") == "Medium"

    def test_evaluate_and_create_are_hard(self):
        assert expected_difficulty("EVALUATE") == "Hard"
        assert expected_difficulty("CREATE") == "Hard"

    def test_lowercase_bloom_level_is_normalized(self):
        """Callers should always pass canonical upper-case, but be forgiving."""
        assert expected_difficulty("remember") == "Easy"

    def test_unknown_level_falls_back_to_medium(self):
        assert expected_difficulty("WHATEVER") == "Medium"

    def test_none_level_does_not_crash(self):
        assert expected_difficulty(None) == "Medium"


# ---- is_difficulty_mismatch -------------------------------------------------


class TestIsDifficultyMismatch:

    def test_matching_difficulty_is_not_a_mismatch(self):
        # REMEMBER -> Easy, stored 'easy' agrees.
        assert is_difficulty_mismatch("easy", "REMEMBER") is False

    def test_conflicting_difficulty_is_a_mismatch(self):
        # REMEMBER -> Easy, but tagged 'hard' — surfaced as a mismatch.
        assert is_difficulty_mismatch("hard", "REMEMBER") is True

    def test_missing_stored_difficulty_is_not_a_mismatch(self):
        assert is_difficulty_mismatch("", "ANALYZE") is False
        assert is_difficulty_mismatch(None, "ANALYZE") is False

    def test_case_and_whitespace_insensitive(self):
        assert is_difficulty_mismatch("  Medium  ", "APPLY") is False


# ---- summarize_paper_balance ------------------------------------------------


class TestSummarizePaperBalance:

    def test_counts_and_percents_per_band(self):
        questions = [
            {"bloom_level": "REMEMBER"},  # Easy
            {"bloom_level": "UNDERSTAND"},  # Easy
            {"bloom_level": "APPLY"},  # Medium
            {"bloom_level": "CREATE"},  # Hard
        ]
        summary = summarize_paper_balance(questions)
        assert summary["total_questions"] == 4
        assert summary["easy"] == {"count": 2, "percent": 50.0}
        assert summary["medium"] == {"count": 1, "percent": 25.0}
        assert summary["hard"] == {"count": 1, "percent": 25.0}

    def test_empty_paper_is_all_zero_without_dividing_by_zero(self):
        summary = summarize_paper_balance([])
        assert summary["total_questions"] == 0
        assert summary["easy"] == {"count": 0, "percent": 0.0}
        assert summary["hard"] == {"count": 0, "percent": 0.0}

    def test_band_percents_sum_to_about_one_hundred(self):
        questions = [{"bloom_level": lvl} for lvl in ["REMEMBER", "APPLY", "EVALUATE"]]
        summary = summarize_paper_balance(questions)
        total_pct = (
            summary["easy"]["percent"] + summary["medium"]["percent"] + summary["hard"]["percent"]
        )
        assert abs(total_pct - 100.0) < 0.5
