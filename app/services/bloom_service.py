"""
Bloom's Taxonomy distribution + marks calculation engine.

Distribution percentages yahan se reuse ki gayi hain (Harsha20033 repo se
reverse-engineer kar ke), kyunki ye exact wahi standard split hai jo
original spec document mein bhi diya gaya tha (20/20/20/15/15/10).
"""

import math

BLOOM_LEVELS = {
    "REMEMBER": {
        "name": "Remember",
        "code": "CO1",
        "description": "Recall facts and basic concepts",
    },
    "UNDERSTAND": {
        "name": "Understand",
        "code": "CO2",
        "description": "Explain ideas and concepts",
    },
    "APPLY": {"name": "Apply", "code": "CO3", "description": "Use information in new situations"},
    "ANALYZE": {"name": "Analyze", "code": "CO4", "description": "Draw connections among ideas"},
    "EVALUATE": {"name": "Evaluate", "code": "CO5", "description": "Justify a stand or decision"},
    "CREATE": {"name": "Create", "code": "CO6", "description": "Produce new or original work"},
}


def calculate_bloom_distribution(dist_type: str, total_questions: int) -> dict:
    """Given a distribution type (balanced/foundational/advanced) and a total
    question count, returns how many questions should belong to each Bloom
    level."""
    distributions = {
        "balanced": {
            "REMEMBER": math.ceil(total_questions * 0.20),
            "UNDERSTAND": math.ceil(total_questions * 0.20),
            "APPLY": math.ceil(total_questions * 0.20),
            "ANALYZE": math.ceil(total_questions * 0.15),
            "EVALUATE": math.ceil(total_questions * 0.15),
            "CREATE": math.ceil(total_questions * 0.10),
        },
        "foundational": {
            "REMEMBER": math.ceil(total_questions * 0.40),
            "UNDERSTAND": math.ceil(total_questions * 0.30),
            "APPLY": math.ceil(total_questions * 0.20),
            "ANALYZE": math.ceil(total_questions * 0.10),
            "EVALUATE": 0,
            "CREATE": 0,
        },
        "advanced": {
            "REMEMBER": math.ceil(total_questions * 0.10),
            "UNDERSTAND": math.ceil(total_questions * 0.15),
            "APPLY": math.ceil(total_questions * 0.20),
            "ANALYZE": math.ceil(total_questions * 0.25),
            "EVALUATE": math.ceil(total_questions * 0.20),
            "CREATE": math.ceil(total_questions * 0.10),
        },
    }
    result = distributions.get(dist_type, distributions["balanced"])

    # Rounding (ceil on each level) can push the total slightly above
    # total_questions, especially for small counts — trim the surplus off
    # the largest buckets (looping, since one bucket alone may not be
    # enough) so the paper always has exactly the requested number.
    surplus = sum(result.values()) - total_questions
    while surplus > 0:
        largest_level = max(result, key=result.get)
        if result[largest_level] == 0:
            break  # nothing left to trim, total_questions is unreachable with this split
        take = min(surplus, result[largest_level])
        result[largest_level] -= take
        surplus -= take

    return result


def calculate_marks(bloom_level: str, question_type: str, difficulty: str) -> int:
    """Simple heuristic: higher cognitive levels and harder difficulty get
    more marks. Tweak these numbers freely once you have real exam data."""
    base = {"REMEMBER": 1, "UNDERSTAND": 2, "APPLY": 3, "ANALYZE": 4, "EVALUATE": 4, "CREATE": 5}
    type_bonus = {
        "essay": 3,
        "short-answer": 1,
        "multiple-choice": 0,
        "true-false": 0,
        "fill-blank": 0,
    }
    diff_bonus = {"easy": 0, "medium": 1, "hard": 2}
    return (
        base.get(bloom_level, 2) + type_bonus.get(question_type, 0) + diff_bonus.get(difficulty, 1)
    )
