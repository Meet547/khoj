#!/usr/bin/env python3
"""Exercise the actual B1 HTTP handlers with REAL providers; never opens a microphone.

Only out.mp3 is retained. Transcripts/extractions are printed, never persisted.
Run from any directory using the backend virtualenv; .env is resolved explicitly.
"""

import argparse
import asyncio
import json
import math
import statistics
import sys
import time
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.audio import duration_s  # noqa: E402
from app.config import Settings  # noqa: E402
from app.main import create_app  # noqa: E402

SAMPLE = ROOT.parent / "artifacts/b1/hindi-synthetic-8s.wav"


async def smoke(sample: Path, output: Path, runs: int = 1) -> dict[str, Any]:
    settings = Settings(_env_file=ROOT / ".env")
    if not settings.gnani_key.get_secret_value() or not settings.ollama_key.get_secret_value():
        raise ValueError("Set GNANI_API_KEY and OLLAMA_API_KEY in the environment or backend .env")
    if not await asyncio.to_thread(sample.is_file):
        raise ValueError(f"Supply an 8-second Hindi WAV at {sample}, or pass --sample PATH")
    data = await asyncio.to_thread(sample.read_bytes)
    seconds = duration_s(data)
    if not 7.5 <= seconds <= 8.5:
        raise ValueError("The Hindi sample must be approximately 8 seconds")
    print(f"Sample: {sample} ({seconds:.2f}s); microphone recording: none", flush=True)
    # A fresh dev cache forces a REAL TTS call on every smoke run, without retaining
    # test cache objects or requiring R2 credentials. Redis limits/budgets stay real.
    with TemporaryDirectory(prefix="khoj-live-") as cache:
        settings = settings.model_copy(
            update={"env": "development", "r2_endpoint": "", "tts_cache_dir": Path(cache)}
        )
        app = create_app(settings)
        start = time.perf_counter()
        async with app.router.lifespan_context(app):
            probe_ms = round((time.perf_counter() - start) * 1000)
            capabilities = app.state.capabilities.report
            print(f"Probe: {probe_ms} ms; missing models: {capabilities['missing']}", flush=True)
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app), base_url="http://localhost", timeout=300
            ) as client:

                async def stage(path: str, **kwargs: Any) -> tuple[httpx.Response, int]:
                    start = time.perf_counter()
                    response = await client.post(path, **kwargs)
                    latency = round((time.perf_counter() - start) * 1000)
                    if response.status_code != 200:
                        error = response.json().get("error", {})
                        raise RuntimeError(
                            f"{path}: HTTP {response.status_code} {error.get('code')} "
                            f"retryable={error.get('retryable')}"
                        )
                    return response, latency

                measurements = []
                for run_index in range(runs):
                    settings.tts_cache_dir = Path(cache) / str(run_index)
                    print(f"Run {run_index + 1}/{runs}", flush=True)
                    stt, stt_ms = await stage(
                        "/api/voice/stt",
                        files={"audio": (sample.name, data, "audio/wav")},
                        data={"lang": "hi"},
                    )
                    transcript = stt.json()["transcript"]
                    print(
                        f"STT: {stt_ms} ms; model=prisma-v3.0; Hindi transcript: {transcript}",
                        flush=True,
                    )
                    if stt.json()["empty"] or not any(
                        "\u0900" <= ch <= "\u097f" for ch in transcript
                    ):
                        raise RuntimeError("Expected a nonempty Hindi transcript")
                    turn, turn_ms = await stage(
                        "/api/llm/turn", json={"transcript": transcript, "lang": "hi"}
                    )
                    extraction = turn.json()
                    print(
                        f"Turn: {turn_ms} ms; model={extraction['model']}; grounded extraction: "
                        + json.dumps(extraction, ensure_ascii=False),
                        flush=True,
                    )
                    if not extraction["fields"]:
                        raise RuntimeError("Expected at least one grounded extracted field")
                    tts, tts_ms = await stage(
                        "/api/voice/tts",
                        json={
                            "text": "नमस्ते। आपकी जानकारी मिल गई है। केस नंबर KHJ-2026-04821 है।",
                            "lang": "hi",
                        },
                    )
                    if not tts.content or not tts.headers["content-type"].startswith("audio/mpeg"):
                        raise RuntimeError("Expected MP3 audio")
                    await asyncio.to_thread(output.write_bytes, tts.content)
                    print(
                        f"TTS: {tts_ms} ms; model={settings.tts_model}; voice={settings.tts_voice}; "
                        f"cache={tts.headers['x-tts-cache']}; wrote {output} ({len(tts.content)} bytes)",
                        flush=True,
                    )
                    result = {
                        "probe_ms": probe_ms,
                        "stt_ms": stt_ms,
                        "turn_ms": turn_ms,
                        "tts_ms": tts_ms,
                        "model": extraction["model"],
                        "trail": extraction.get("trail", []),
                        "attempts": extraction.get("attempts", []),
                        "extraction": extraction,
                        "transcript": transcript,
                        "output": str(output),
                    }
                    measurements.append(
                        {
                            k: result[k]
                            for k in ("stt_ms", "turn_ms", "tts_ms", "model", "trail", "attempts")
                        }
                    )
                percentiles = {}
                for stage_name in ("stt_ms", "turn_ms", "tts_ms"):
                    ordered = sorted(row[stage_name] for row in measurements)
                    percentiles[stage_name] = {
                        "p50": statistics.median(ordered),
                        "p95": ordered[math.ceil(0.95 * len(ordered)) - 1],
                    }
                print(
                    "Latency percentiles (milliseconds; p95 nearest rank): "
                    + json.dumps(percentiles),
                    flush=True,
                )
                return {
                    **result,
                    "runs": runs,
                    "measurements": measurements,
                    "percentiles": percentiles,
                }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sample", type=Path, default=SAMPLE)
    parser.add_argument("--output", type=Path, default=Path("out.mp3"))
    parser.add_argument(
        "--runs", type=int, default=20, help="Number of real-provider runs (default 20)."
    )
    parser.add_argument(
        "--report", type=Path, help="Optional latency-only JSON report (no transcript)."
    )
    args = parser.parse_args()
    if not 1 <= args.runs <= 100:
        parser.error("--runs must be between 1 and 100")
    try:
        result = asyncio.run(smoke(args.sample.resolve(), args.output.resolve(), args.runs))
        if args.report:
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.report.write_text(
                json.dumps(
                    {k: result[k] for k in ("runs", "model", "measurements", "percentiles")},
                    indent=2,
                )
            )
    except Exception as exc:
        # Never print provider exception bodies, environment values or credentials.
        if isinstance(exc, (ValueError, RuntimeError)):
            print(str(exc), file=sys.stderr)
        else:
            print(
                f"Smoke failed: {type(exc).__name__}. Check provider connectivity and Redis.",
                file=sys.stderr,
            )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
