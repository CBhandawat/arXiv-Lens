import json
import os
from groq import Groq


SYSTEM_PROMPT = """You are a podcast script writer for a show called "ArXiv Cast" where two hosts discuss AI research papers.

HOST_A is "Priya" — the expert. She explains concepts clearly and is enthusiastic about the research.
HOST_B is "Ravi" — the curious learner. He asks the questions a smart non-researcher would ask: "wait, but why?", "can you give me an analogy?", "so what does this actually change?".

Rules:
- Write exactly 8–10 dialogue turns (alternating Priya and Ravi, Priya starts).
- Priya's turns: 2–4 sentences. Clear, jargon-free where possible, or explains jargon inline.
- Ravi's turns: 1–2 sentences. Genuine curious questions or short reactions.
- No filler phrases like "Great question!" or "Absolutely!".
- End with Priya giving a punchy 1-sentence "why this matters" takeaway.
- Output ONLY valid JSON. No markdown fences. No preamble. No trailing text.

JSON format:
{
  "title": "<short podcast episode title>",
  "turns": [
    {"host": "Priya", "text": "..."},
    {"host": "Ravi",  "text": "..."}
  ]
}"""


def generate_script(title: str, abstract: str) -> dict:
    """
    Takes paper title + abstract, returns a podcast script dict:
    {
        "title": str,
        "turns": [{"host": "Priya"|"Ravi", "text": str}, ...]
    }
    Raises ValueError on parse failure.
    """
    client = Groq(api_key=os.environ["GROQ_API_KEY"])

    user_msg = f"""Paper title: {title}

Abstract:
{abstract}

Write the ArXiv Cast podcast script for this paper."""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": user_msg},
        ],
        temperature=0.75,
        max_tokens=1200,
    )

    raw = response.choices[0].message.content.strip()

    # Strip accidental markdown fences
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    try:
        script = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"LLM returned invalid JSON: {e}\n\nRaw output:\n{raw}")

    # Basic validation
    if "turns" not in script or not isinstance(script["turns"], list):
        raise ValueError("Script missing 'turns' list")

    return script
