import asyncio
import shutil
import subprocess

import pytest

from app.config import Settings
from app.schemas import Extraction, FieldValue, ground
from scripts.smoke_live import ROOT, SAMPLE, smoke


@pytest.mark.live
async def test_real_hindi_stt_grounded_turn_and_playable_tts(tmp_path):
    settings = Settings(_env_file=ROOT / ".env")
    if not settings.gnani_key.get_secret_value() or not settings.ollama_key.get_secret_value():
        pytest.skip("Set GNANI_API_KEY and OLLAMA_API_KEY")
    output = tmp_path / "out.mp3"
    result = await smoke(SAMPLE, output)
    assert all(result[k] > 0 for k in ("stt_ms", "turn_ms", "tts_ms"))
    fields = [FieldValue(**f) for f in result["extraction"]["fields"]]
    kept, dropped = ground(result["transcript"], Extraction(fields=fields))
    assert kept and not dropped
    assert shutil.which("ffmpeg"), "ffmpeg is required to verify MP3 playback"
    await asyncio.to_thread(
        subprocess.run,
        ["ffmpeg", "-v", "error", "-i", str(output), "-f", "null", "-"],
        check=True,
        capture_output=True,
    )
