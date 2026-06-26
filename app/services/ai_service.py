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
import os
import json
import requests
from dotenv import load_dotenv

# Project root ki .env file se GEMINI_API_KEY / ANTHROPIC_API_KEY load karta
# hai. Ye line module-level os.environ.get() calls se PEHLE chalni zaroori
# hai, warna keys None reh jayengi.
load_dotenv()

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_MODEL = "claude-sonnet-4-6"


def build_prompt(topic: str, subject: str, bloom_distribution: dict, question_types: list, difficulty: str) -> str:
    bloom_lines = "\n".join(
        f"- {level}: {count} questions" for level, count in bloom_distribution.items() if count > 0
    )
    types_str = ", ".join(question_types)

    return f"""You are an expert bilingual (English + Urdu) educational content creator for a school in Swat, Pakistan, specializing in Bloom's Taxonomy-based question design.

SUBJECT: {subject}
TOPIC: {topic}
DIFFICULTY: {difficulty}
QUESTION TYPES TO USE: {types_str}

GENERATE QUESTIONS WITH THIS BLOOM'S TAXONOMY DISTRIBUTION:
{bloom_lines}

INSTRUCTIONS:
1. Every question must be written in BOTH English and proper Urdu script (not Roman Urdu).
2. Tag every question with its correct Bloom level from: REMEMBER, UNDERSTAND, APPLY, ANALYZE, EVALUATE, CREATE.
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


def _extract_json(text: str) -> list:
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
            "Kam questions (e.g. 5-6) ke saath dobara try karen. Raw response (first 300 chars): "
            + text[:300]
        )

    try:
        parsed = json.loads(cleaned[json_start:json_end])
    except json.JSONDecodeError:
        raise ValueError(
            "AI response truncate ho gaya lagta hai (JSON incomplete hai). "
            "Kam questions (e.g. 5-6) ke saath dobara try karen, ya difficulty/distribution "
            "simple rakhen. Raw response (first 300 chars): " + text[:300]
        )

    return parsed.get("questions", [])


def _generate_with_gemini(prompt: str) -> list:
    response = requests.post(
        f"{GEMINI_API_URL}?key={GEMINI_API_KEY}",
        headers={"Content-Type": "application/json"},
        json={
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.7, "maxOutputTokens": 16000},
        },
        timeout=60,
    )
    response.raise_for_status()
    data = response.json()

    try:
        text = data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError) as e:
        raise ValueError(f"Gemini response samajh nahi aaya: {data}") from e

    return _extract_json(text)


def _generate_with_claude(prompt: str) -> list:
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
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=60,
    )
    response.raise_for_status()
    data = response.json()

    text = "".join(
        block.get("text", "") for block in data.get("content", []) if block.get("type") == "text"
    )
    return _extract_json(text)


def generate_questions_from_ai(topic: str, subject: str, bloom_distribution: dict, question_types: list, difficulty: str) -> list:
    prompt = build_prompt(topic, subject, bloom_distribution, question_types, difficulty)

    if ANTHROPIC_API_KEY:
        return _generate_with_claude(prompt)

    if GEMINI_API_KEY:
        return _generate_with_gemini(prompt)

    raise RuntimeError(
        "Koi API key set nahi hai. .env file mein GEMINI_API_KEY (free) ya "
        "ANTHROPIC_API_KEY (paid) dalen."
    )
