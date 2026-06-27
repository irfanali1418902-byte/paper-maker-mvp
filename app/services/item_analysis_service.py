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


# ---- Phase B: Difficulty Index (P) + Discrimination Index (D) ---------------
#
# Both indices are generalized to partial-credit items (questions carry
# varying max marks, not just right/wrong) by working in proportion-of-marks:
#   P = mean marks / max marks
#   D = (top group mean − bottom group mean) / max marks

# P-value bands (proportion 0..1). Outside [too_hard, too_easy] the item is
# flagged. Tune against real Swat exam data.
P_TOO_HARD = 0.30
P_TOO_EASY = 0.85

# D-index uses the classic top/bottom 27% split. Below this many students the
# split is statistically meaningless, so we still compute D but mark it
# unreliable (UI greys it out rather than acting on it).
DISCRIMINATION_GROUP_FRACTION = 0.27
MIN_STUDENTS_FOR_RELIABLE_D = 10


def difficulty_index(average_marks: float, max_marks: float) -> float:
    """P-value = average marks / max marks, in 0..1. Higher = easier item.
    max_marks 0 (shouldn't happen) yields 0.0 instead of dividing by zero."""
    if max_marks <= 0:
        return 0.0
    return round(average_marks / max_marks, 2)


def discrimination_index(student_scores: list[tuple[float, float]], max_marks: float) -> float:
    """D-index in -1..1. `student_scores` is one (student_total, marks_on_this_
    question) pair per student who attempted the item. We rank by total score,
    take the top and bottom 27% (at least 1 each, never overlapping), and
    return (top mean − bottom mean) / max_marks. Undefined cases give 0.0."""
    n = len(student_scores)
    if n < 2 or max_marks <= 0:
        return 0.0

    ordered = sorted(student_scores, key=lambda s: s[0], reverse=True)
    # 27% rounded, but never let the two groups overlap (matters at small n).
    group_size = min(max(1, round(n * DISCRIMINATION_GROUP_FRACTION)), n // 2)

    top = ordered[:group_size]
    bottom = ordered[-group_size:]
    top_mean = sum(marks for _, marks in top) / group_size
    bottom_mean = sum(marks for _, marks in bottom) / group_size
    return round((top_mean - bottom_mean) / max_marks, 2)


def is_d_reliable(student_count: int) -> bool:
    """True jab itne students hon ke top/bottom split meaningful ho."""
    return student_count >= MIN_STUDENTS_FOR_RELIABLE_D


def classify_p(p_value: float) -> str:
    """too_hard / good / too_easy."""
    if p_value < P_TOO_HARD:
        return "too_hard"
    if p_value > P_TOO_EASY:
        return "too_easy"
    return "good"


def classify_d(d_index: float) -> str:
    """problematic (negative) / poor / acceptable / good / excellent."""
    if d_index < 0:
        return "problematic"
    if d_index < 0.20:
        return "poor"
    if d_index < 0.30:
        return "acceptable"
    if d_index < 0.40:
        return "good"
    return "excellent"


def flag_question(p_band: str, d_band: str, d_reliable: bool) -> str | None:
    """Human-readable reason(s) ke saath bad question ko flag karta hai, warna
    None. Unreliable D (chhoti class) par discrimination-based flag nahi
    lagate — sirf P-value waale."""
    reasons: list[str] = []
    if p_band == "too_hard":
        reasons.append("bahut mushkil (P-value kam)")
    elif p_band == "too_easy":
        reasons.append("bahut aasaan (P-value zyada)")

    if d_reliable:
        if d_band == "problematic":
            reasons.append("ulta discriminate (D negative — key galat ho sakti hai)")
        elif d_band == "poor":
            reasons.append("kamzor discrimination (D < 0.20)")

    return "; ".join(reasons) if reasons else None
