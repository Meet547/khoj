"""Browsers record WebM/Opus (Chrome) or MP4/AAC (Safari). Gnani accepts WAV/MP3/OGG/FLAC/AAC/M4A, max 30 s,
so every upload is converted to 16 kHz mono WAV first. Requires ffmpeg in the container image.
ffmpeg writes WAV headers with unknown length to a pipe, so we take raw PCM and build the header ourselves."""

import io
import subprocess
import wave

MAX_SECONDS = 30
RATE = 16000


class AudioError(Exception):
    pass


def to_wav16k(data: bytes) -> bytes:
    p = subprocess.run(
        [
            "ffmpeg",
            "-nostdin",
            "-loglevel",
            "error",
            "-i",
            "pipe:0",
            "-ac",
            "1",
            "-ar",
            str(RATE),
            "-t",
            str(MAX_SECONDS + 1),
            "-f",
            "s16le",
            "pipe:1",
        ],
        input=data,
        capture_output=True,
        timeout=20,
    )
    if p.returncode != 0 or not p.stdout:
        raise AudioError("Could not decode audio")
    if len(p.stdout) / (RATE * 2) > MAX_SECONDS:
        raise AudioError("Audio longer than 30 seconds")
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(p.stdout)
    return buf.getvalue()


def duration_s(wav: bytes) -> float:
    with wave.open(io.BytesIO(wav)) as w:
        return float(w.getnframes()) / float(w.getframerate())
