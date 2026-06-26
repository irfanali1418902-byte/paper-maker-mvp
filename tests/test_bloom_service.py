"""Unit tests for bloom_service — pure functions, no DB needed.

The rounding-overflow case is the historically important one: `ceil` on
each bucket can push the sum above `total_questions`. The trim loop must
bring it back. We sweep small totals exhaustively because that's where the
bug originally surfaced.
"""
from app.services.bloom_service import calculate_bloom_distribution, calculate_marks


# ---- calculate_bloom_distribution -------------------------------------------

class TestCalculateBloomDistribution:

    def test_balanced_distribution_sum_equals_total(self):
        dist = calculate_bloom_distribution("balanced", 10)
        assert sum(dist.values()) == 10

    def test_all_six_bloom_levels_present(self):
        """All six keys must always exist, even when count is 0 — callers
        iterate `dist.items()` and expect every level."""
        dist = calculate_bloom_distribution("balanced", 10)
        assert set(dist.keys()) == {
            "REMEMBER", "UNDERSTAND", "APPLY", "ANALYZE", "EVALUATE", "CREATE",
        }

    def test_balanced_total_one_handles_rounding_overflow(self):
        """The classic bug: for total=1, ceil on each of 6 buckets yielded
        1*6=6. The trim loop must reduce it back to 1."""
        dist = calculate_bloom_distribution("balanced", 1)
        assert sum(dist.values()) == 1

    def test_balanced_small_totals_never_overflow(self):
        """Sweep small N exhaustively — overflow only surfaces at low counts."""
        for n in range(0, 25):
            dist = calculate_bloom_distribution("balanced", n)
            assert sum(dist.values()) == n, f"overflow at n={n}: got {dist}"

    def test_foundational_keeps_evaluate_and_create_at_zero(self):
        """Foundational is for young learners — EVALUATE/CREATE never asked."""
        dist = calculate_bloom_distribution("foundational", 30)
        assert dist["EVALUATE"] == 0
        assert dist["CREATE"] == 0

    def test_foundational_small_totals_never_overflow(self):
        for n in range(0, 25):
            dist = calculate_bloom_distribution("foundational", n)
            assert sum(dist.values()) == n, f"foundational overflow at n={n}: got {dist}"

    def test_advanced_small_totals_never_overflow(self):
        for n in range(0, 25):
            dist = calculate_bloom_distribution("advanced", n)
            assert sum(dist.values()) == n, f"advanced overflow at n={n}: got {dist}"

    def test_unknown_dist_type_falls_back_to_balanced(self):
        """Typo in dist_type shouldn't crash — fallback to balanced."""
        unknown = calculate_bloom_distribution("nonsense-mode", 10)
        balanced = calculate_bloom_distribution("balanced", 10)
        assert unknown == balanced

    def test_zero_total_returns_all_zeros(self):
        dist = calculate_bloom_distribution("balanced", 0)
        assert sum(dist.values()) == 0
        assert all(v == 0 for v in dist.values())

    def test_all_bucket_counts_are_non_negative(self):
        """The trim loop must not produce negative counts at any N or split."""
        for n in range(0, 50):
            for dist_type in ["balanced", "foundational", "advanced"]:
                dist = calculate_bloom_distribution(dist_type, n)
                for level, count in dist.items():
                    assert count >= 0, (
                        f"negative count at n={n}, dist={dist_type}, "
                        f"level={level}: {count}"
                    )

    def test_large_total_balanced_proportions(self):
        """At large N, rounding error is negligible — proportions should be
        close to the documented 20/20/20/15/15/10 split."""
        dist = calculate_bloom_distribution("balanced", 100)
        assert sum(dist.values()) == 100
        # Pre-trim ceil ratios are close to the spec; post-trim values must
        # still sum exactly and stay within a couple of the targets.
        assert 18 <= dist["REMEMBER"] <= 22
        assert 18 <= dist["UNDERSTAND"] <= 22
        assert 8 <= dist["CREATE"] <= 12


# ---- calculate_marks --------------------------------------------------------

class TestCalculateMarks:

    def test_remember_easy_mcq_is_one(self):
        """REMEMBER (1) + multiple-choice (0) + easy (0) = 1."""
        assert calculate_marks("REMEMBER", "multiple-choice", "easy") == 1

    def test_analyze_hard_essay_is_nine(self):
        """ANALYZE (4) + essay (3) + hard (2) = 9."""
        assert calculate_marks("ANALYZE", "essay", "hard") == 9

    def test_create_hard_essay_is_highest(self):
        """CREATE (5) + essay (3) + hard (2) = 10 — highest documented combo."""
        assert calculate_marks("CREATE", "essay", "hard") == 10

    def test_unknown_bloom_level_falls_back_to_default_two(self):
        """Unknown level → base default 2."""
        assert calculate_marks("WHATEVER", "multiple-choice", "easy") == 2

    def test_unknown_question_type_gives_zero_bonus(self):
        assert calculate_marks("REMEMBER", "unknown-type", "easy") == 1

    def test_unknown_difficulty_falls_back_to_default_one(self):
        """Unknown difficulty defaults to bonus 1 (medium-equivalent)."""
        assert calculate_marks("REMEMBER", "multiple-choice", "unknown") == 2

    def test_short_answer_adds_one_mark(self):
        """UNDERSTAND (2) + short-answer (1) + medium (1) = 4."""
        assert calculate_marks("UNDERSTAND", "short-answer", "medium") == 4
