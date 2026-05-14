import os
from twilio.rest import Client


def send_whatsapp_digest(episodes: list[dict]) -> None:
    """
    Send a WhatsApp message with links to all 5 podcast episodes.

    episodes: list of dicts with keys:
        - title (str)
        - arxiv_url (str)
        - audio_url (str)   ← presigned S3 URL
    """
    client = Client(
        os.environ["TWILIO_ACCOUNT_SID"],
        os.environ["TWILIO_AUTH_TOKEN"],
    )

    lines = ["🎙 *ArXiv Cast — Daily Digest*\n"]
    for i, ep in enumerate(episodes, 1):
        lines.append(f"*{i}. {ep['title'][:60]}{'…' if len(ep['title']) > 60 else ''}*")
        lines.append(f"🔬 {ep['arxiv_url']}")
        lines.append(f"🎧 {ep['audio_url']}\n")

    body = "\n".join(lines)

    client.messages.create(
        from_=os.environ["TWILIO_WHATSAPP_FROM"],
        to=os.environ["WHATSAPP_TO"],
        body=body,
    )
    print(f"[whatsapp] Sent digest with {len(episodes)} episodes.")
