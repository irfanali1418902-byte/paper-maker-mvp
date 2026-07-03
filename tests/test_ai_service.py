"""Unit tests for ai_service — pure prompt building + provider dispatch.

build_prompt() network ko touch nahi karti, is liye ye offline test hoti hai —
prompt-design ka contract yahan lock karte hain. Provider-dispatch tests
_call_ai/_call_gemini ko mock keys + stubbed HTTP se check karte hain (koi
real network call nahi). Note: dispatch selection-by-priority hai (Anthropic
key jeette to Claude, warna Gemini) — runtime "fallback on failure" nahi hai;
provider fail ho to AIGenerationFailed uthti hai, doosre provider par nahi
jaati."""

import pytest
import requests

from app.services import ai_service
from app.services.ai_service import build_prompt
from app.services.exceptions import AIGenerationFailed

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


# ---- provider dispatch (_call_ai) — priority selection, not fallback --------


def _record_provider(calls, name, out):
    def stub(prompt, image=None):
        calls.append(name)
        return out

    return stub


def test_call_ai_prefers_claude_when_both_keys_set(monkeypatch):
    calls: list = []
    monkeypatch.setattr(ai_service, "ANTHROPIC_API_KEY", "anthropic-key")
    monkeypatch.setattr(ai_service, "GEMINI_API_KEY", "gemini-key")
    monkeypatch.setattr(ai_service, "_call_claude", _record_provider(calls, "claude", "claude-out"))
    monkeypatch.setattr(ai_service, "_call_gemini", _record_provider(calls, "gemini", "gemini-out"))

    assert ai_service._call_ai("prompt") == "claude-out"
    assert calls == ["claude"]  # Gemini ko haath tak nahi lagaya


def test_call_ai_uses_gemini_when_only_gemini_key(monkeypatch):
    calls: list = []
    monkeypatch.setattr(ai_service, "ANTHROPIC_API_KEY", None)
    monkeypatch.setattr(ai_service, "GEMINI_API_KEY", "gemini-key")
    monkeypatch.setattr(ai_service, "_call_claude", _record_provider(calls, "claude", "claude-out"))
    monkeypatch.setattr(ai_service, "_call_gemini", _record_provider(calls, "gemini", "gemini-out"))

    assert ai_service._call_ai("prompt") == "gemini-out"
    assert calls == ["gemini"]


def test_call_ai_raises_when_no_keys(monkeypatch):
    monkeypatch.setattr(ai_service, "ANTHROPIC_API_KEY", None)
    monkeypatch.setattr(ai_service, "GEMINI_API_KEY", None)
    with pytest.raises(RuntimeError, match="API key"):
        ai_service._call_ai("prompt")


# ---- HTTP error wrapping — provider failure -> AIGenerationFailed, key-safe --


def test_gemini_http_error_becomes_ai_generation_failed(monkeypatch):
    monkeypatch.setattr(ai_service, "GEMINI_API_KEY", "secret-gemini-key")

    def boom(*args, **kwargs):
        raise requests.exceptions.ConnectionError(
            "connect to generativelanguage.googleapis.com fail"
        )

    monkeypatch.setattr(ai_service.requests, "post", boom)
    with pytest.raises(AIGenerationFailed) as exc:
        ai_service._call_gemini("prompt")

    msg = str(exc.value)
    assert "secret-gemini-key" not in msg  # key never leaks to the teacher-facing message
    assert "googleapis" not in msg  # nor the URL


def test_claude_http_error_becomes_ai_generation_failed(monkeypatch):
    monkeypatch.setattr(ai_service, "ANTHROPIC_API_KEY", "secret-anthropic-key")

    def boom(*args, **kwargs):
        raise requests.exceptions.ConnectionError("connect to api.anthropic.com fail")

    monkeypatch.setattr(ai_service.requests, "post", boom)
    with pytest.raises(AIGenerationFailed) as exc:
        ai_service._call_claude("prompt")

    msg = str(exc.value)
    assert "secret-anthropic-key" not in msg
    assert "anthropic.com" not in msg


def _err_with_status(status):
    return requests.exceptions.HTTPError(response=_FakeResponse(status) if status else None)


class _FakeResponse:
    def __init__(self, status_code):
        self.status_code = status_code


def test_provider_error_message_maps_status_and_never_leaks():
    busy = ai_service._provider_error_message("Gemini", _err_with_status(503))
    generic = ai_service._provider_error_message("Claude", _err_with_status(400))
    network = ai_service._provider_error_message("Gemini", _err_with_status(None))

    assert "503" in busy and "busy" in busy.lower()
    assert "400" in generic
    assert "network" in network.lower()
    for m in (busy, generic, network):
        assert "googleapis" not in m and "anthropic.com" not in m
