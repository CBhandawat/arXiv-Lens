import os
import requests


LEMONFOX_API_URL = "https://api.lemonfox.ai/v1/audio/speech"

# Assign distinct voices to each host.
# Lemonfox uses OpenAI-compatible voice names — adjust if their catalogue differs.
VOICE_MAP = {
    "Priya": "nova",    # warm, clear female voice
    "Ravi":  "onyx",    # deeper male voice
}

# Fallback if host name not found
DEFAULT_VOICE = "alloy"


def synthesize_turn(text: str, host: str) -> bytes:
    """
    Call Lemonfox TTS API for a single dialogue turn.
    Returns raw MP3 bytes.
    Raises requests.HTTPError on API failure.
    """
    api_key = os.environ["LEMONFOX_API_KEY"]
    voice = VOICE_MAP.get(host, DEFAULT_VOICE)

    payload = {
        "model": "tts-1",          # Lemonfox model name — update if they use a different identifier
        "input": text,
        "voice": voice,
        "response_format": "mp3",
        "speed": 1.0,
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    resp = requests.post(LEMONFOX_API_URL, json=payload, headers=headers, timeout=30)
    resp.raise_for_status()

    return resp.content  # raw MP3 bytes


def synthesize_script(turns: list[dict]) -> list[bytes]:
    """
    Synthesize all turns in a script.
    turns: [{"host": "Priya"|"Ravi", "text": str}, ...]
    Returns list of MP3 byte strings in order.
    """
    audio_chunks = []
    for i, turn in enumerate(turns):
        print(f"[tts] Synthesizing turn {i+1}/{len(turns)} — {turn['host']}")
        chunk = synthesize_turn(turn["text"], turn["host"])
        audio_chunks.append(chunk)
    return audio_chunks
