#!/usr/bin/env python3
"""Pre-generate static intake speech, including sentence fragments, before serving traffic."""

import argparse
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.config import Settings  # noqa: E402
from app.graph.audio import sentences  # noqa: E402
from app.graph.resources import Resources  # noqa: E402
from app.integrations.gnani import Gnani, tts_prepare  # noqa: E402
from app.integrations.storage import Storage, tts_key  # noqa: E402


async def pregen(settings: Settings, languages: list[str]) -> dict[str, int]:
    resources = Resources()
    gnani = Gnani(
        settings.gnani_key.get_secret_value(),
        settings.gnani_base,
        tts_slots=settings.gnani_tts_slots,
    )
    storage = Storage(settings)
    counts = {"generated": 0, "cached": 0}
    try:
        for lang in languages:
            resources.language(lang, production=settings.env == "production")
            texts = resources.static_sentences(lang)
            texts |= {part for text in list(texts) for part in sentences(text)}

            async def one(text: str, lang: str = lang) -> None:
                key = tts_key(
                    text, lang, settings.tts_voice, settings.tts_model, settings.tts_speed
                )
                if await storage.get(key) is not None:
                    counts["cached"] += 1
                    return
                data = await gnani.speak(
                    tts_prepare(text, lang),
                    ui_lang=lang,
                    voice=settings.tts_voice,
                    model=settings.tts_model,
                    speed=settings.tts_speed,
                )
                await storage.put(key, data)
                counts["generated"] += 1

            # Keep admission bounded as well as the provider's internal semaphore.
            ordered = sorted(texts)
            for index in range(0, len(ordered), settings.gnani_tts_slots):
                await asyncio.gather(
                    *(one(text) for text in ordered[index : index + settings.gnani_tts_slots])
                )
            print(f"{lang}: {len(texts)} static utterances prepared", flush=True)
        print(counts, flush=True)
        return counts
    finally:
        await gnani.aclose()
        await storage.aclose()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--langs",
        default="en,hi",
        help="Comma-separated languages, or all (review gates apply in production).",
    )
    args = parser.parse_args()
    settings = Settings(_env_file=ROOT / ".env")
    langs = list(Resources().templates) if args.langs == "all" else args.langs.split(",")
    asyncio.run(pregen(settings, langs))


if __name__ == "__main__":
    main()
