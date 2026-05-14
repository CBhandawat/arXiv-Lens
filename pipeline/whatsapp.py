import os
import base64
import time
import requests

WASENDER_API_URL = "https://www.wasenderapi.com/api"


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {os.environ['WASENDER_API_KEY']}",
        "Content-Type": "application/json",
    }


def _upload_mp3(mp3_bytes: bytes) -> str:
    """
    Upload raw MP3 bytes to WASenderAPI's media hosting.
    Returns a public URL valid for 24 hours.
    """
    upload_url = f"{WASENDER_API_URL}/upload"

    # Use JSON/Base64 upload method
    b64_data = base64.b64encode(mp3_bytes).decode("utf-8")
    payload = {
        "base64": f"data:audio/mpeg;base64,{b64_data}",
    }

    resp = requests.post(upload_url, json=payload, headers=_headers(), timeout=60)
    resp.raise_for_status()

    data = resp.json()
    if not data.get("success"):
        raise RuntimeError(f"WASenderAPI upload failed: {data}")

    return data["publicUrl"]


def send_whatsapp_episode(mp3_bytes: bytes, title: str, episode_num: int, total: int) -> None:
    """
    Send a single podcast episode as a WhatsApp audio (voice note) message
    via WASenderAPI.

    Flow:
      1. Upload MP3 bytes → get a temporary public URL from WASenderAPI.
      2. Send a text caption message first.
      3. Send the audio message using the public URL.
    """
    to = os.environ["WHATSAPP_TO"]

    # Step 1: Upload audio and get public URL
    print(f"[whatsapp] Uploading episode {episode_num}/{total}...")
    audio_url = _upload_mp3(mp3_bytes)

    caption = (
        f"🎙 *ArXiv Cast — Episode {episode_num}/{total}*\n"
        f"📄 {title[:80]}{'…' if len(title) > 80 else ''}"
    )

    # Step 2: Send caption as a text message
    text_payload = {
        "to": to,
        "text": caption,
    }
    resp = requests.post(
        f"{WASENDER_API_URL}/send-message",
        json=text_payload,
        headers=_headers(),
        timeout=30,
    )
    resp.raise_for_status()

    # Step 3: Send audio as a voice note
    audio_payload = {
        "to": to,
        "audioUrl": audio_url,
    }
    resp = requests.post(
        f"{WASENDER_API_URL}/send-message",
        json=audio_payload,
        headers=_headers(),
        timeout=30,
    )
    resp.raise_for_status()

    data = resp.json()
    if not data.get("success"):
        raise RuntimeError(f"WASenderAPI send failed: {data}")

    print(f"[whatsapp] Sent episode {episode_num}/{total}: {title[:50]}")


def send_whatsapp_digest(episodes: list[dict]) -> None:
    """
    Send each episode as a separate WhatsApp audio message via WASenderAPI.

    episodes: list of dicts with keys:
        - title      (str)
        - arxiv_url  (str)
        - mp3_bytes  (bytes)
    """
    total = len(episodes)
    to = os.environ["WHATSAPP_TO"]

    # Send a header message first
    header_payload = {
        "to": to,
        "text": f"🎙 *ArXiv Cast — Daily Digest*\nSending {total} podcast episode(s) now...",
    }
    resp = requests.post(
        f"{WASENDER_API_URL}/send-message",
        json=header_payload,
        headers=_headers(),
        timeout=30,
    )
    resp.raise_for_status()

    # Send each episode
    for i, ep in enumerate(episodes, 1):
        send_whatsapp_episode(
            mp3_bytes=ep["mp3_bytes"],
            title=ep["title"],
            episode_num=i,
            total=total,
        )
        # Small delay between episodes to avoid rate limits
        if i < total:
            time.sleep(1.5)
