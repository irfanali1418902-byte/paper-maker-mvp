"""Unit tests for item_analysis_service Phase A — pure functions, no DB.

Phase A covers expected difficulty from Bloom level, stored-vs-expected
mismatch detection, and the paper balance summary.
"""

from app.services.item_analysis_service import (
    classify_d,
    classify_p,
    difficulty_index,
    discrimination_index,
    expected_difficulty,
    flag_question,
    is_d_reliable,
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


# ---- difficulty_index (P-value) ---------------------------------------------


class TestDifficultyIndex:

    def test_all_full_marks_is_one(self):
        # Everyone scored the full 5 → P = 1.0 (very easy).
        assert difficulty_index(5.0, 5) == 1.0

    def test_half_marks_is_point_five(self):
        assert difficulty_index(2.5, 5) == 0.5

    def test_zero_average_is_zero(self):
        assert difficulty_index(0.0, 5) == 0.0

    def test_zero_max_marks_does_not_divide_by_zero(self):
        assert difficulty_index(3.0, 0) == 0.0


# ---- discrimination_index (D) -----------------------------------------------


class TestDiscriminationIndex:

    def test_perfect_discrimination(self):
        # Top scorer aced the item, bottom scorer missed it entirely.
        scores = [(10.0, 1.0), (2.0, 0.0)]
        assert discrimination_index(scores, 1) == 1.0

    def test_negative_when_low_scorers_outperform(self):
        # The strong student missed it, the weak student got it — D negative,
        # a classic mis-keyed/ambiguous item signal.
        scores = [(10.0, 0.0), (2.0, 1.0)]
        assert discrimination_index(scores, 1) == -1.0

    def test_no_discrimination_when_everyone_equal(self):
        scores = [(10.0, 1.0), (8.0, 1.0), (4.0, 1.0), (2.0, 1.0)]
        assert discrimination_index(scores, 1) == 0.0

    def test_single_student_is_undefined_zero(self):
        assert discrimination_index([(5.0, 1.0)], 1) == 0.0

    def test_groups_never_overlap_at_small_n(self):
        # n=3, 27% rounds to 1 → top 1 vs bottom 1, middle ignored.
        scores = [(9.0, 1.0), (5.0, 1.0), (1.0, 0.0)]
        # top mean 1, bottom mean 0 → D = 1.0 over max 1.
        assert discrimination_index(scores, 1) == 1.0


# ---- classify_p / classify_d ------------------------------------------------


class TestClassifyP:

    def test_too_hard_below_threshold(self):
        assert classify_p(0.29) == "too_hard"

    def test_good_in_band(self):
        assert classify_p(0.30) == "good"
        assert classify_p(0.85) == "good"

    def test_too_easy_above_threshold(self):
        assert classify_p(0.86) == "too_easy"


class TestClassifyD:

    def test_negative_is_problematic(self):
        assert classify_d(-0.1) == "problematic"

    def test_bands(self):
        assert classify_d(0.10) == "poor"
        assert classify_d(0.25) == "acceptable"
        assert classify_d(0.35) == "good"
        assert classify_d(0.45) == "excellent"


# ---- is_d_reliable ----------------------------------------------------------


class TestIsDReliable:

    def test_small_class_is_unreliable(self):
        assert is_d_reliable(3) is False

    def test_ten_students_is_reliable(self):
        assert is_d_reliable(10) is True


# ---- flag_question ----------------------------------------------------------


class TestFlagQuestion:

    def test_good_item_is_not_flagged(self):
        assert flag_question("good", "good", True) is None

    def test_too_hard_is_flagged(self):
        assert "mushkil" in flag_question("too_hard", "good", True)

    def test_negative_d_is_flagged_when_reliable(self):
        flag = flag_question("good", "problematic", True)
        assert flag is not None and "negative" in flag

    def test_unreliable_d_does_not_trigger_discrimination_flag(self):
        # Small class: poor D alone shouldn't flag the item.
        assert flag_question("good", "poor", False) is None

    def test_combines_multiple_reasons(self):
        flag = flag_question("too_easy", "problematic", True)
        assert "aasaan" in flag and "negative" in flag
