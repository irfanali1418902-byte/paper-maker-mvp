"""
Bilingual (Urdu + English), Bloom-tagged questions generate karne wala
module. Do providers support karta hai:

  - GEMINI_API_KEY set ho -> Google Gemini use hoga (FREE, no credit card)
  - ANTHROPIC_API_KEY set ho -> Claude use hoga (paid, behtar quality)
  - Agar dono set hain -> Claude ko priority milti hai (jab production mein
    behtar quality chahiye ho, sirf Claude key add kar den, code khud switch
    ho jayega)

Reference repo (Harsha20033) ke createAIPrompt() se prompt-design ka idea
liya gaya hai (structured JSON output mangwana), bilingual instruction
add ki gayi hai.
"""

import base64
import json
import os

import requests
from dotenv import load_dotenv

from app.repositories import usage_log_repository
from app.services.exceptions import AIGenerationFailed

# Project root ki .env file se GEMINI_API_KEY / ANTHROPIC_API_KEY load karta
# hai. Ye line module-level os.environ.get() calls se PEHLE chalni zaroori
# hai, warna keys None reh jayengi.
load_dotenv()

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_API_URL = (
    f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
)

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_MODEL = "claude-sonnet-4-6"

# Difficulty sirf marks ka multiplier nahi — har level ki cognitive gehraai
# ko bhi shape karti hai. Distribution counts authoritative rehti hain; ye
# guidance batati hai ke un counts ke andar har question kitna gehra ho.
DIFFICULTY_GUIDANCE = {
    "easy": (
        "Natural emphasis: REMEMBER and UNDERSTAND. Single-step reasoning, "
        "short direct wording, vocabulary a struggling student can follow. "
        "If the distribution requires a higher level (APPLY/ANALYZE/EVALUATE/"
        "CREATE), make it the gentlest possible version of that level — one "
        "familiar step, no trick wording."
    ),
    "medium": (
        "Natural emphasis: UNDERSTAND, APPLY, and light ANALYZE. Two-step "
        "reasoning is fine; keep wording clear and avoid trick phrasing. "
        "Lower levels stay concrete; higher levels stay grounded in a single "
        "familiar context."
    ),
    "hard": (
        "Natural emphasis: ANALYZE, EVALUATE, and CREATE. Multi-step reasoning "
        "that connects ideas or justifies a position. Even REMEMBER/UNDERSTAND "
        "questions should demand precise recall or a subtle distinction."
    ),
}


def build_prompt(
    topic: str, subject: str, bloom_distribution: dict, question_types: list, difficulty: str
) -> str:
    bloom_lines = "\n".join(
        f"- {level}: {count} questions" for level, count in bloom_distribution.items() if count > 0
    )
    types_str = ", ".join(question_types)
    difficulty_guidance = DIFFICULTY_GUIDANCE.get(difficulty, DIFFICULTY_GUIDANCE["medium"])

    return f"""You are an expert bilingual (English + Urdu) educational content creator for a school in Swat, Pakistan, specializing in Bloom's Taxonomy-based question design.

SUBJECT: {subject}
TOPIC: {topic}
DIFFICULTY: {difficulty}
QUESTION TYPES TO USE: {types_str}

DIFFICULTY CALIBRATION:
{difficulty_guidance}

GENERATE QUESTIONS WITH THIS BLOOM'S TAXONOMY DISTRIBUTION:
{bloom_lines}

INSTRUCTIONS:
1. Every question must be written in BOTH English and proper Urdu script (not Roman Urdu).
2. Tag every question with its correct Bloom level from: REMEMBER, UNDERSTAND, APPLY, ANALYZE, EVALUATE, CREATE. Each question's cognitive depth must match the DIFFICULTY CALIBRATION above while still honouring the requested Bloom distribution counts.
3. For multiple-choice questions, include exactly 4 options (English and Urdu) with one correct answer.
4. Provide a short explanation for the correct answer, in both languages.
5. Keep language age-appropriate for school students.
6. IMPORTANT for young learners (counting, numbers, shapes, simple objects topics): if the
   question is naturally about counting or identifying a small number (1-20) of real-world
   objects (fruits, animals, toys, shapes), include "visual_emoji" (a single matching emoji,
   e.g. "🍎", "🐒", "⭐") and "visual_count" (how many to display) so the question can show a
   picture row instead of just text — exactly like a real textbook would. If the question is
   abstract or doesn't suit this, set both to null.
7. Respond with ONLY a valid JSON object. No extra text, no markdown formatting, no commentary.

RESPONSE FORMAT (JSON ONLY):
{{
  "questions": [
    {{
      "bloom_level": "REMEMBER",
      "question_type": "multiple-choice",
      "question_en": "...",
      "question_ur": "...",
      "options_en": ["...", "...", "...", "..."],
      "options_ur": ["...", "...", "...", "..."],
      "correct_answer_en": "...",
      "correct_answer_ur": "...",
      "explanation_en": "...",
      "explanation_ur": "...",
      "visual_emoji": "🍎",
      "visual_count": 5
    }}
  ]
}}"""


# Text aur image dono extraction same fields/format maangte hain — sirf source
# (raw text vs page image) farq hai, isliye rules ek hi jagah.
_SYLLABUS_EXTRACTION_RULES = """INSTRUCTIONS:
1. Identify each unit/chapter and the sub-topics under it.
2. For every sub-topic, output one object with these exact fields:
   - "unit_no": integer unit/chapter number (best guess; if none, use 1).
   - "unit_title": the unit/chapter title.
   - "subtopic_title": the specific topic/lesson title.
   - "activity_type": classify the cognitive demand as EXACTLY one of
     "Introduction" (new concept, recall), "Identification" (recognise/name),
     "Practice" (apply/solve), or "Review" (analyse/evaluate). Pick the best fit.
   - "page_no": page number as an integer if visible, else null.
   - "page_range": page range string like "12-18" if visible, else null.
   - "learning_outcome": a short (max 15 words) outcome of what the student learns. If none stated, write a concise inferred one.
3. Do NOT invent topics that aren't shown. Skip headers, prefaces, indexes, and answer keys.
4. Respond with ONLY a valid JSON object. No markdown, no commentary.

RESPONSE FORMAT (JSON ONLY):
{
  "topics": [
    {
      "unit_no": 1,
      "unit_title": "...",
      "subtopic_title": "...",
      "activity_type": "Introduction",
      "page_no": 5,
      "page_range": "5-9",
      "learning_outcome": "..."
    }
  ]
}"""


def build_syllabus_extraction_prompt(syllabus_text: str, subject: str, grade: str) -> str:
    return f"""You are a curriculum analyst. Below is the raw text extracted from a {subject} syllabus / textbook contents for {grade}. Extract a clean, structured list of teachable topics.

RAW SYLLABUS TEXT:
\"\"\"
{syllabus_text}
\"\"\"

{_SYLLABUS_EXTRACTION_RULES}"""


def build_syllabus_image_prompt(subject: str, grade: str) -> str:
    return f"""You are a curriculum analyst. The attached image is a page from a {subject} syllabus / textbook contents for {grade}. Read it carefully (perform OCR if needed) and extract a clean, structured list of teachable topics.

{_SYLLABUS_EXTRACTION_RULES}"""


def _provider_error_message(provider: str, err: Exception) -> str:
    """Turn a requests-level failure into a short, key-free message safe to
    show a teacher. Never include the URL or response body — the Gemini URL
    used to carry the API key, and provider error bodies can echo it back."""
    status = getattr(getattr(err, "response", None), "status_code", None)
    if status in (429, 503):
        return (
            f"{provider} abhi busy/overloaded hai (HTTP {status}). Thodi der baad dobara try karen."
        )
    if status:
        return f"{provider} ne error diya (HTTP {status}). Thodi der baad dobara try karen."
    return f"{provider} se connect nahi ho saka (network/timeout). Dobara try karen."


def _extract_json(text: str, key: str = "questions") -> list:
    # Gemini/Claude kabhi-kabhi ```json ... ``` fences mein wrap kar dete hain
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("```", 2)[1] if cleaned.count("```") >= 2 else cleaned.lstrip("`")
        cleaned = cleaned.lstrip("json").strip()

    json_start = cleaned.find("{")
    json_end = cleaned.rfind("}") + 1

    if json_start == -1 or json_end == 0:
        raise ValueError(
            "AI response mein valid JSON nahi mila — shayad response truncate ho gaya "
            "(token limit kam padh gayi) ya AI ne format follow nahi kiya. "
            "Chhote input (kam items/pages) ke saath dobara try karen. "
            "Raw response (first 300 chars): " + text[:300]
        )

    try:
        parsed = json.loads(cleaned[json_start:json_end])
    except json.JSONDecodeError as e:
        raise ValueError(
            "AI response truncate ho gaya lagta hai (JSON incomplete hai). "
            "Chhote input (kam items/pages) ke saath dobara try karen. "
            "Raw response (first 300 chars): " + text[:300]
        ) from e

    return parsed.get(key, [])


def _call_gemini(prompt: str, image: tuple | None = None) -> str:
    # Key header mein bhejte hain (URL mein nahi) taake kisi error message ya
    # log mein leak na ho — pehle ?key= URL mein tha aur 503 par expose ho raha tha.
    parts: list = [{"text": prompt}]
    if image is not None:
        mime_type, raw = image
        parts = [
            {"inline_data": {"mime_type": mime_type, "data": base64.b64encode(raw).decode()}},
            {"text": prompt},
        ]
    try:
        response = requests.post(
            GEMINI_API_URL,
            headers={"Content-Type": "application/json", "x-goog-api-key": GEMINI_API_KEY},
            json={
                "contents": [{"parts": parts}],
                "generationConfig": {"temperature": 0.7, "maxOutputTokens": 16000},
            },
            timeout=120,
        )
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        raise AIGenerationFailed(_provider_error_message("Gemini", e)) from e
    data = response.json()

    # Billing-grade usage log lands here — provider already charged for the
    # tokens, so log before any further parsing that could raise.
    usage = data.get("usageMetadata", {})
    usage_log_repository.insert(
        provider="gemini",
        model=GEMINI_MODEL,
        status="success",
        input_tokens=usage.get("promptTokenCount"),
        output_tokens=usage.get("candidatesTokenCount"),
        total_tokens=usage.get("totalTokenCount"),
    )

    try:
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError) as e:
        raise ValueError(f"Gemini response samajh nahi aaya: {data}") from e


def _call_claude(prompt: str, image: tuple | None = None) -> str:
    content: object = prompt
    if image is not None:
        mime_type, raw = image
        content = [
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": mime_type,
                    "data": base64.b64encode(raw).decode(),
                },
            },
            {"type": "text", "text": prompt},
        ]
    try:
        response = requests.post(
            ANTHROPIC_API_URL,
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": ANTHROPIC_MODEL,
                "max_tokens": 8000,
                "messages": [{"role": "user", "content": content}],
            },
            timeout=120,
        )
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        raise AIGenerationFailed(_provider_error_message("Claude", e)) from e
    data = response.json()

    # Anthropic returns input + output tokens separately; compute total
    # ourselves when both are present so the column stays comparable to
    # the Gemini case.
    usage = data.get("usage", {})
    input_t = usage.get("input_tokens")
    output_t = usage.get("output_tokens")
    total_t = (input_t + output_t) if input_t is not None and output_t is not None else None
    usage_log_repository.insert(
        provider="claude",
        model=ANTHROPIC_MODEL,
        status="success",
        input_tokens=input_t,
        output_tokens=output_t,
        total_tokens=total_t,
    )

    return "".join(
        block.get("text", "") for block in data.get("content", []) if block.get("type") == "text"
    )


def _call_ai(prompt: str, image: tuple | None = None) -> str:
    """Provider dispatch — Anthropic key set ho to Claude, warna Gemini.
    Optional image (mime_type, raw_bytes) vision-capable models ko bheji jaati
    hai. Returns raw model text; JSON parsing caller karta hai (_extract_json)."""
    if ANTHROPIC_API_KEY:
        return _call_claude(prompt, image)
    if GEMINI_API_KEY:
        return _call_gemini(prompt, image)
    raise RuntimeError(
        "Koi API key set nahi hai. .env file mein GEMINI_API_KEY (free) ya "
        "ANTHROPIC_API_KEY (paid) dalen."
    )


def generate_questions_from_ai(
    topic: str, subject: str, bloom_distribution: dict, question_types: list, difficulty: str
) -> list:
    prompt = build_prompt(topic, subject, bloom_distribution, question_types, difficulty)
    return _extract_json(_call_ai(prompt), key="questions")


def extract_topics_from_text(syllabus_text: str, subject: str, grade: str) -> list:
    """Syllabus/textbook ke raw text se structured topics nikalta hai
    (syllabus_topics row ki shape mein). AI provider use hota hai — JSON list
    of dicts return karta hai jise syllabus_service DB mein save karta hai."""
    prompt = build_syllabus_extraction_prompt(syllabus_text, subject, grade)
    return _extract_json(_call_ai(prompt), key="topics")


def extract_topics_from_image(image_bytes: bytes, mime_type: str, subject: str, grade: str) -> list:
    """Syllabus page ki image (JPG/PNG) se topics nikalta hai — vision-capable
    model image ko OCR+samajh kar wahi structured shape return karta hai jo
    text extraction deti hai."""
    prompt = build_syllabus_image_prompt(subject, grade)
    return _extract_json(_call_ai(prompt, image=(mime_type, image_bytes)), key="topics")
