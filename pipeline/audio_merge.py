import io
import subprocess
import tempfile
import os


TURN_GAP_MS = 600
HOST_SWITCH_GAP_MS = 900


def merge_audio(chunks: list[bytes], turns: list[dict]) -> bytes:
    with tempfile.TemporaryDirectory() as tmp:
        file_list = []

        for i, (chunk, turn) in enumerate(zip(chunks, turns)):
            # Write audio chunk
            chunk_path = os.path.join(tmp, f"turn_{i}.mp3")
            with open(chunk_path, "wb") as f:
                f.write(chunk)
            file_list.append(chunk_path)

            # Write silence gap
            if i < len(chunks) - 1:
                prev_host = turn["host"]
                next_host = turns[i + 1]["host"]
                gap_ms = HOST_SWITCH_GAP_MS if prev_host != next_host else TURN_GAP_MS
                gap_path = os.path.join(tmp, f"gap_{i}.mp3")
                subprocess.run([
                    "ffmpeg", "-y", "-f", "lavfi",
                    "-i", f"anullsrc=r=24000:cl=mono",
                    "-t", str(gap_ms / 1000),
                    "-q:a", "9", "-acodec", "libmp3lame",
                    gap_path
                ], check=True, capture_output=True)
                file_list.append(gap_path)

        # Write concat list
        list_path = os.path.join(tmp, "files.txt")
        with open(list_path, "w") as f:
            for p in file_list:
                f.write(f"file '{p}'\n")

        # Merge
        out_path = os.path.join(tmp, "output.mp3")
        subprocess.run([
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", list_path, "-c", "copy", out_path
        ], check=True, capture_output=True)

        with open(out_path, "rb") as f:
            return f.read()
