"""Unit tests for adaptive_service (Phase 3) — pure functions, no DB.

The distribution must always sum to the requested total, weight questions
toward weak levels, and let the floor keep strong levels represented.
"""

from app.services.adaptive_service import build_adaptive_distribution, summarize

# A representative class profile, mirroring the design preview.
PROFILE = [
    {"bloom_level": "REMEMBER", "average_percent": 90.0},
    {"bloom_level": "UNDERSTAND", "average_percent": 80.0},
    {"bloom_level": "APPLY", "average_percent": 50.0},
    {"bloom_level": "ANALYZE", "average_percent": 40.0},
    {"bloom_level": "EVALUATE", "average_percent": 30.0},
    {"bloom_level": "CREATE", "average_percent": 85.0},
]


class TestBuildAdaptiveDistribution:

    def test_sums_to_total(self):
        for total in range(0, 30):
            dist = build_adaptive_distribution(PROFILE, total)
            assert sum(dist.values()) == total, f"mismatch at total={total}: {dist}"

    def test_matches_design_preview(self):
        """floor_weight=20 must reproduce the blended preview the user approved."""
        dist = build_adaptive_distribution(PROFILE, 10)
        assert dist == {
            "REMEMBER": 1,
            "UNDERSTAND": 1,
            "APPLY": 2,
            "ANALYZE": 2,
            "EVALUATE": 3,
            "CREATE": 1,
        }

    def test_weaker_levels_get_at_least_as_many_as_stronger(self):
        dist = build_adaptive_distribution(PROFILE, 12)
        # EVALUATE (30%) is the weakest -> should get the most.
        assert dist["EVALUATE"] == max(dist.values())
        # A strong level should never out-allocate a clearly weaker one.
        assert dist["ANALYZE"] >= dist["REMEMBER"]

    def test_floor_keeps_strong_levels_represented(self):
        """With enough questions, even the strongest level gets a share —
        the floor prevents the paper collapsing onto weak levels."""
        dist = build_adaptive_distribution(PROFILE, 12)
        assert dist["REMEMBER"] >= 1

    def test_empty_breakdown_returns_empty(self):
        assert build_adaptive_distribution([], 10) == {}

    def test_zero_total_returns_empty(self):
        assert build_adaptive_distribution(PROFILE, 0) == {}

    def test_all_levels_perfect_falls_back_to_floor_split(self):
        """If the class aced everything, weakness is 0 everywhere — the floor
        still produces a valid distribution summing to total."""
        perfect = [{"bloom_level": lvl, "average_percent": 100.0} for lvl in ["REMEMBER", "APPLY"]]
        dist = build_adaptive_distribution(perfect, 6)
        assert sum(dist.values()) == 6


class TestSummarize:

    def test_orders_weakest_first(self):
        dist = build_adaptive_distribution(PROFILE, 10)
        summary = summarize(PROFILE, dist)
        percents = [row["average_percent"] for row in summary]
        assert percents == sorted(percents)
        assert summary[0]["bloom_level"] == "EVALUATE"  # weakest

    def test_carries_allocation_per_level(self):
        dist = build_adaptive_distribution(PROFILE, 10)
        summary = summarize(PROFILE, dist)
        for row in summary:
            assert row["questions_allocated"] == dist[row["bloom_level"]]
