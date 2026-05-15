import os
import time
import requests


WASENDER_API_URL = "https://www.wasenderapi.com/api"


def _auth_headers() -> dict:
    return {
        "Authorization": f"Bearer {os.environ['WASENDER_API_KEY']}",
    }


def _upload_mp3(mp3_bytes: bytes) -> str:
    """
    Upload raw MP3 bytes to WASenderAPI using raw binary upload (recommended method).
    Returns a public URL valid for 24 hours.
    """
    resp = requests.post(
        f"{WASENDER_API_URL}/upload",
        headers={
            **_auth_headers(),
            "Content-Type": "audio/mpeg",
        },
        data=mp3_bytes,   # raw binary — no base64 needed
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json()

    if not data.get("success"):
        raise RuntimeError(f"WASenderAPI upload failed: {data}")

    return data["publicUrl"]


def send_whatsapp_episode(mp3_bytes: bytes, title: str, episode_num: int, total: int) -> None:
    """
    Send a single podcast episode as a WhatsApp audio (voice note) message.
    Flow:
      1. Upload MP3 → get temporary public URL (24h)
      2. Send text caption
      3. Send audio message with the URL
    """
    to = os.environ["WHATSAPP_TO"]   # plain E.164: +91XXXXXXXXXX (no whatsapp: prefix)

    # Step 1: Upload
    print(f"[whatsapp] Uploading episode {episode_num}/{total}...")
    audio_url = _upload_mp3(mp3_bytes)
    print(f"[whatsapp] Uploaded → {audio_url}")

    # Step 2: Send caption
    caption = (
        f"🎙 *ArXiv Cast — Episode {episode_num}/{total}*\n"
        f"📄 {title[:80]}{'…' if len(title) > 80 else ''}"
    )
    resp = requests.post(
        f"{WASENDER_API_URL}/send-message",
        headers={**_auth_headers(), "Content-Type": "application/json"},
        json={"to": to, "text": caption},
        timeout=30,
    )
    resp.raise_for_status()

    # Step 3: Send audio
    resp = requests.post(
        f"{WASENDER_API_URL}/send-message",
        headers={**_auth_headers(), "Content-Type": "application/json"},
        json={"to": to, "audioUrl": audio_url},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()

    if not data.get("success"):
        raise RuntimeError(f"WASenderAPI send failed: {data}")

    print(f"[whatsapp] ✓ Sent episode {episode_num}/{total}: {title[:50]}")


def send_whatsapp_digest(episodes: list[dict]) -> None:
    """
    Send a header message then each episode as a caption + audio pair.

    episodes: list of dicts with keys:
        - title      (str)
        - arxiv_url  (str)
        - mp3_bytes  (bytes)
    """
    to = os.environ["WHATSAPP_TO"]
    total = len(episodes)

    # Header message
    resp = requests.post(
        f"{WASENDER_API_URL}/send-message",
        headers={**_auth_headers(), "Content-Type": "application/json"},
        json={
            "to": to,
            "text": f"🎙 *ArXiv Cast — Daily Digest*\nSending {total} podcast episodes now...",
        },
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
        if i < total:
            time.sleep(2)  # avoid rate limits between episodes
