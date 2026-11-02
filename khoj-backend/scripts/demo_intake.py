#!/usr/bin/env python3
"""Record a synthetic Hindi intake, SIGKILL twice, then resume and save a real case.

--fake is the deterministic CI mode. Omit it for REAL Gnani/Ollama calls.
Uses DATABASE_URL and Redis from the environment/backend .env; run migrations first.
"""

import argparse
import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.config import Settings  # noqa: E402
from app.graph.audio import sentences  # noqa: E402
from app.graph.resources import Resources  # noqa: E402
from app.integrations.gnani import Gnani  # noqa: E402
from app.integrations.ollama import OllamaClient  # noqa: E402
from app.main import create_app  # noqa: E402
from scripts.intake_demo_data import CONVERSATIONS, fake_model  # noqa: E402
from scripts.pregen_tts import pregen  # noqa: E402


async def worker(args):
    settings = Settings(_env_file=ROOT / ".env")
    settings.tts_cache_dir = Path(args.cache)
    gnani = (
        Gnani(
            "fake",
            transport=httpx.MockTransport(
                lambda r: httpx.Response(
                    200, content=b"ID3demo", headers={"content-type": "audio/mpeg"}
                )
            ),
        )
        if args.fake
        else None
    )
    ollama = (
        OllamaClient("https://ollama.test", "", transport=httpx.MockTransport(fake_model))
        if args.fake
        else None
    )
    app = create_app(settings, gnani=gnani, ollama=ollama)
    context = (
        json.loads(await asyncio.to_thread(Path(args.context).read_text))
        if await asyncio.to_thread(Path(args.context).exists)
        else {"record": []}
    )
    async with app.router.lifespan_context(app):
        if args.fake:
            for sentence in Resources().static_sentences("hi"):
                for part in {sentence, *sentences(sentence)}:
                    await app.state.storage.put(
                        app.state.intake_audio.key(part, "hi"), b"ID3static-demo"
                    )
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app), base_url="https://localhost", timeout=300
        ) as client:
            if context.get("cookie"):
                client.cookies.set(
                    "khoj_intake", context["cookie"], domain="localhost.local", path="/api"
                )

            async def call(path, **kwargs):
                response = await client.post(path, **kwargs)
                if response.status_code != 200:
                    raise RuntimeError(f"{path}: {response.status_code} {response.text}")
                return response.json()

            if args.phase == "start":
                context["sessionId"] = (
                    await call("/api/session", json={"kind": "missing", "lang": "hi"})
                )["sessionId"]
                context["cookie"] = client.cookies.get("khoj_intake")
            if args.phase in {"start", "readback"}:
                indexes = range(2) if args.phase == "start" else range(2, 4)
                for index in indexes:
                    text = CONVERSATIONS["hi"][index][0]
                    result = await call(
                        "/api/turn",
                        data={"sessionId": context["sessionId"], "text": text},
                        headers={"Idempotency-Key": f"demo:{index}"},
                    )
                    context["record"].append({"input": text, **result})
                if args.phase == "readback" and result["stage"] != "readback":
                    raise RuntimeError("Expected a durable confirmation interrupt")
            else:
                await call("/api/auth/otp/send", json={"phone": "9000000001"})
                await call("/api/auth/otp/verify", json={"phone": "9000000001", "code": "123456"})
                result = await call(
                    "/api/confirm", json={"sessionId": context["sessionId"], "consent": True}
                )
                context["result"] = result
            path = Path(args.context)
            await asyncio.to_thread(path.write_text, json.dumps(context, ensure_ascii=False))
            await asyncio.to_thread(path.chmod, 0o600)
            print(
                json.dumps(
                    {
                        "ready": args.phase,
                        "sessionId": context["sessionId"],
                        "caseNo": context.get("result", {}).get("caseNo"),
                    }
                ),
                flush=True,
            )
            if args.phase != "confirm":
                # Parent deliberately kills us without lifespan cleanup after the checkpoint.
                await asyncio.Event().wait()
    if gnani:
        await gnani.aclose()
    if ollama:
        await ollama.aclose()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fake", action="store_true")
    parser.add_argument("--output", type=Path, default=ROOT.parent / "artifacts/b2/hindi-demo.json")
    parser.add_argument("--phase", choices=["start", "readback", "confirm"])
    parser.add_argument("--context")
    parser.add_argument("--cache")
    args = parser.parse_args()
    if args.phase:
        asyncio.run(worker(args))
        return
    with TemporaryDirectory(prefix="khoj-demo-") as directory:
        context = Path(directory) / "context.json"
        cache = Path(directory) / "tts"
        if not args.fake:
            config = Settings(_env_file=ROOT / ".env")
            cache = Path(args.cache) if args.cache else config.tts_cache_dir
            config.tts_cache_dir = cache
            asyncio.run(pregen(config, ["hi"]))
        for phase in ["start", "readback", "confirm"]:
            command = [
                sys.executable,
                str(Path(__file__).resolve()),
                "--phase",
                phase,
                "--context",
                str(context),
                "--cache",
                str(cache),
            ]
            if args.fake:
                command.append("--fake")
            child = subprocess.Popen(
                command,
                cwd=ROOT,
                stdout=subprocess.PIPE,
                stderr=None,
                text=True,
                env=os.environ.copy(),
            )
            try:
                ready = False
                for line in child.stdout:
                    print(line, end="", flush=True)
                    if '"ready"' in line:
                        ready = True
                        break
                if not ready:
                    raise RuntimeError(f"Demo phase {phase} failed")
                if phase != "confirm":
                    child.kill()
                    print(
                        f"SIGKILL after {phase}; restarting from PostgreSQL checkpoint", flush=True
                    )
                child.wait(timeout=30)
            finally:
                if child.poll() is None:
                    child.kill()
                    child.wait()
        data = json.loads(context.read_text())
        # Omit private guest/auth credentials from the recorded artifact.
        data.pop("cookie", None)
        data["mode"] = "fake" if args.fake else "live"
        data["process_kills"] = 2
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(data, ensure_ascii=False, indent=2))
        print(f"Created {data['result']['caseNo']}; recorded {args.output}")


if __name__ == "__main__":
    main()
