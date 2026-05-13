import io
from pydub import AudioSegment


# Silence gap between turns (milliseconds)
TURN_GAP_MS = 600

# Slightly longer gap between host switches (gives a natural conversational pause)
HOST_SWITCH_GAP_MS = 900


def merge_audio(chunks: list[bytes], turns: list[dict]) -> bytes:
    """
    Merge a list of MP3 byte chunks into a single MP3.
    Inserts silence gaps between turns, with longer gaps on host switches.

    Args:
        chunks: list of raw MP3 bytes, one per dialogue turn
        turns:  list of {"host": str, "text": str} dicts (same order as chunks)

    Returns:
        Single MP3 as bytes
    """
    combined = AudioSegment.empty()

    for i, (chunk, turn) in enumerate(zip(chunks, turns)):
        segment = AudioSegment.from_file(io.BytesIO(chunk), format="mp3")

        if i > 0:
            prev_host = turns[i - 1]["host"]
            curr_host = turn["host"]
            gap_ms = HOST_SWITCH_GAP_MS if prev_host != curr_host else TURN_GAP_MS
            combined += AudioSegment.silent(duration=gap_ms)

        combined += segment

    # Export to bytes
    output = io.BytesIO()
    combined.export(output, format="mp3", bitrate="128k")
    return output.getvalue()
