"""Item analysis (psychometrics) — pure functions, no IO.

Phase A (here): expected item difficulty from Bloom level + paper balance
summary, used at paper-build time.

Phase B (later): actual Difficulty Index (P-value) and Discrimination Index
(D) computed from uploaded results will live in this same module.

All thresholds are module-level constants so they can be tuned against real
Swat exam data without touching the logic.
"""

# Bloom level -> predicted difficulty band. Lower cognitive levels are
# expected easier; higher ones harder. This is a *prediction*, independent of
# the difficulty a teacher/AI tagged at generation time — a mismatch between
# the two is itself a useful signal.
EXPECTED_DIFFICULTY_BY_BLOOM = {
    "REMEMBER": "Easy",
    "UNDERSTAND": "Easy",
    "APPLY": "Medium",
    "ANALYZE": "Medium",
    "EVALUATE": "Hard",
    "CREATE": "Hard",
}

DIFFICULTY_BANDS = ("Easy", "Medium", "Hard")

# Unknown / missing Bloom level falls back here rather than crashing.
_DEFAULT_BAND = "Medium"


def expected_difficulty(bloom_level: str) -> str:
    """Bloom level se predicted difficulty band (Easy/Medium/Hard)."""
    return EXPECTED_DIFFICULTY_BY_BLOOM.get((bloom_level or "").upper(), _DEFAULT_BAND)


def is_difficulty_mismatch(stored_difficulty: str, bloom_level: str) -> bool:
    """True jab generation-time tagged difficulty Bloom-expected band se alag
    ho (e.g. ek 'hard' tagged REMEMBER question). Stored difficulty na ho to
    mismatch nahi maante."""
    if not stored_difficulty:
        return False
    return stored_difficulty.strip().capitalize() != expected_difficulty(bloom_level)


def summarize_paper_balance(questions: list[dict]) -> dict:
    """Count + percent of questions per expected difficulty band — teacher ko
    ek nazar mein paper ka Easy/Medium/Hard balance dikhata hai."""
    total = len(questions)
    counts = {band: 0 for band in DIFFICULTY_BANDS}
    for q in questions:
        counts[expected_difficulty(q.get("bloom_level"))] += 1

    return {
        "total_questions": total,
        "easy": _band(counts["Easy"], total),
        "medium": _band(counts["Medium"], total),
        "hard": _band(counts["Hard"], total),
    }


def _band(count: int, total: int) -> dict:
    """Ek band ka count + guarded percent (total 0 par ZeroDivision se bachao)."""
    return {"count": count, "percent": round(count / total * 100, 1) if total else 0.0}
