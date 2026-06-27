"""Adaptive paper generation (Phase 3) — pure functions, no IO.

Turns a class's Bloom-level performance (from a results upload's
bloom_breakdown) into a question distribution weighted toward the levels the
class scored worst on. The result feeds the same question-picking the balanced
paper uses, so an adaptive paper is just a balanced paper with a
weakness-derived distribution.

Strategy: "blended with a floor". Each level's weight is a fixed floor plus its
weakness (100 − average_percent). The floor keeps strong levels represented so
the paper still has coverage instead of collapsing onto one weak level; the
weakness term pushes extra questions toward where the class struggled.
"""

# Added to every level's weight. Bigger floor => flatter (more coverage);
# smaller => more aggressive skew toward weak levels. Tunable.
ADAPTIVE_FLOOR_WEIGHT = 20.0


def build_adaptive_distribution(bloom_breakdown: list[dict], total_questions: int) -> dict:
    """bloom_breakdown -> {bloom_level: question_count}, summing exactly to
    total_questions. Empty input or non-positive total yields {}."""
    if total_questions <= 0 or not bloom_breakdown:
        return {}

    weights: dict[str, float] = {}
    for level in bloom_breakdown:
        weakness = max(0.0, 100.0 - level["average_percent"])
        weights[level["bloom_level"]] = ADAPTIVE_FLOOR_WEIGHT + weakness

    return _largest_remainder_allocation(weights, total_questions)


def summarize(bloom_breakdown: list[dict], distribution: dict) -> list[dict]:
    """Per-level (average_percent, questions_allocated), weakest level first —
    lets the UI explain *why* each level got the share it did."""
    summary = [
        {
            "bloom_level": level["bloom_level"],
            "average_percent": level["average_percent"],
            "questions_allocated": distribution.get(level["bloom_level"], 0),
        }
        for level in bloom_breakdown
    ]
    summary.sort(key=lambda row: row["average_percent"])
    return summary


def _largest_remainder_allocation(weights: dict[str, float], total: int) -> dict:
    """Allocate `total` whole items across levels in proportion to weights,
    using the largest-remainder method so the counts sum to exactly `total`."""
    total_weight = sum(weights.values())
    if total_weight <= 0:
        return {level: 0 for level in weights}

    exact = {level: total * w / total_weight for level, w in weights.items()}
    counts = {level: int(value) for level, value in exact.items()}  # floor

    # Hand out the leftover (from flooring) to the largest fractional parts.
    remaining = total - sum(counts.values())
    by_remainder = sorted(weights, key=lambda level: exact[level] - counts[level], reverse=True)
    for level in by_remainder[:remaining]:
        counts[level] += 1
    return counts
