import os
import base64
import tempfile
from twilio.rest import Client


def send_whatsapp_episode(mp3_bytes: bytes, title: str, episode_num: int, total: int) -> None:
    """
    Send a single podcast episode as a WhatsApp audio message via Twilio.
    Twilio requires a publicly accessible media URL, so we base64-encode
    the MP3 and send it as a data URI via MMS.

    For the WhatsApp sandbox, Twilio supports media_url pointing to a
    publicly accessible MP3. We write the file to a temp path and host
    it inline as a base64 data URI.

    NOTE: Twilio WhatsApp media requires a public HTTPS URL.
    The cleanest free approach is to upload to Twilio's own asset hosting
    via their Serverless Assets, or use a public temporary URL.
    This implementation uses Twilio's media parameter with a data URI
    which works for MMS — for WhatsApp, see note below.
    """
    client = Client(
        os.environ["TWILIO_ACCOUNT_SID"],
        os.environ["TWILIO_AUTH_TOKEN"],
    )

    # Write MP3 to a temp file
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
        f.write(mp3_bytes)
        tmp_path = f.name

    caption = (
        f"🎙 *ArXiv Cast — Episode {episode_num}/{total}*\n"
        f"📄 {title[:80]}{'…' if len(title) > 80 else ''}"
    )

    # Upload the MP3 to Twilio and get a hosted URL
    # Twilio allows you to upload media to their CDN via the API
    media = client.content.v1.contents.create(
        friendly_name=f"arxiv_cast_ep{episode_num}",
        content_type="application/json",
        content={
            "schema": {"version": 1, "channel": {"name": "whatsapp"}},
            "body": caption,
            "actions": [],
            "media": [{
                "media_type": "audio/mpeg",
                "body": base64.b64encode(mp3_bytes).decode("utf-8"),
            }],
        },
    )

    client.messages.create(
        from_=os.environ["TWILIO_WHATSAPP_FROM"],
        to=os.environ["WHATSAPP_TO"],
        content_sid=media.sid,
    )

    os.unlink(tmp_path)
    print(f"[whatsapp] Sent episode {episode_num}/{total}: {title[:50]}")


def send_whatsapp_digest(episodes: list[dict]) -> None:
    """
    Send each episode as a separate WhatsApp audio message.

    episodes: list of dicts with keys:
        - title     (str)
        - arxiv_url (str)
        - mp3_bytes (bytes)
    """
    total = len(episodes)

    # Send a header message first
    client = Client(
        os.environ["TWILIO_ACCOUNT_SID"],
        os.environ["TWILIO_AUTH_TOKEN"],
    )
    client.messages.create(
        from_=os.environ["TWILIO_WHATSAPP_FROM"],
        to=os.environ["WHATSAPP_TO"],
        body=f"🎙 *ArXiv Cast — Daily Digest*\nSending {total} podcast episodes now...",
    )

    # Send each episode as a media message
    for i, ep in enumerate(episodes, 1):
        send_whatsapp_episode(
            mp3_bytes=ep["mp3_bytes"],
            title=ep["title"],
            episode_num=i,
            total=total,
        )
