"""Unit tests for the pure prompt-building logic in ai_service.

build_prompt() network ko touch nahi karti, is liye ye offline test hoti hai —
prompt-design ka contract yahan lock karte hain (AI call ka mock alag hai)."""

from app.services.ai_service import build_prompt

_DIST = {"REMEMBER": 2, "UNDERSTAND": 2, "APPLY": 1}


def test_build_prompt_lists_requested_types():
    prompt = build_prompt("Fractions", "Mathematics", _DIST, ["multiple-choice", "essay"], "medium")
    assert "QUESTION TYPES TO USE: multiple-choice, essay" in prompt


def test_build_prompt_has_subjective_guidance():
    # Short-answer/essay ke liye options khali + model answer wali hidayat honi chahiye.
    prompt = build_prompt("Fractions", "Mathematics", _DIST, ["short-answer"], "medium")
    assert "empty arrays" in prompt
    assert "model answer" in prompt


def test_build_prompt_renders_bloom_distribution():
    prompt = build_prompt("Fractions", "Mathematics", _DIST, ["multiple-choice"], "medium")
    assert "REMEMBER: 2 questions" in prompt
    assert "APPLY: 1 questions" in prompt


def test_build_prompt_omits_zero_count_levels():
    dist = {"REMEMBER": 3, "CREATE": 0}
    prompt = build_prompt("Fractions", "Mathematics", dist, ["multiple-choice"], "easy")
    # Sirf bloom-distribution section dekho (difficulty guidance mein bhi CREATE aata hai).
    bloom_section = prompt.split("DISTRIBUTION:")[1].split("INSTRUCTIONS:")[0]
    assert "REMEMBER: 3 questions" in bloom_section
    assert "CREATE" not in bloom_section
