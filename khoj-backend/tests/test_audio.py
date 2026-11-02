import shutil
import subprocess

import pytest

from app.audio import AudioError, duration_s, to_wav16k

pytestmark = pytest.mark.skipif(not shutil.which("ffmpeg"), reason="ffmpeg not installed")


def tone(seconds, fmt):
    p = subprocess.run(
        [
            "ffmpeg",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency=440:duration={seconds}",
            "-f",
            fmt,
            "pipe:1",
        ],
        capture_output=True,
    )
    if p.returncode or not p.stdout:
        pytest.skip(f"ffmpeg cannot encode {fmt} here")
    return p.stdout


def test_webm_to_wav16k_mono():
    out = to_wav16k(tone(2, "webm"))
    assert out[:4] == b"RIFF" and 1.8 < duration_s(out) < 2.2


def test_rejects_over_30s_and_garbage():
    with pytest.raises(AudioError):
        to_wav16k(tone(35, "webm"))
    with pytest.raises(AudioError):
        to_wav16k(b"not audio")
