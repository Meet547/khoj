import argparse
import asyncio
import collections
import hashlib
import json
import re
import unicodedata
from pathlib import Path

from app.capabilities import Capabilities
from app.config import get_settings
from app.graph.resources import Resources
from app.integrations.ollama import OllamaClient
from app.llm import LLM, LLMUnavailable
from app.schemas import Extraction, ground, is_grounded

backend = Path(__file__).resolve().parents[1]
out = backend.parent / "artifacts/speech-eval"
prereg = out / "field_recovery_preregistration.md"
digest = hashlib.sha256(prereg.read_bytes()).hexdigest()
assert digest == "4414eb309b3b06a69cbb0549e4f5bc1c3f7860ad33ea2e2af56608e142c48a2f"


def jsonl(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]


fields = ("name", "age", "gender", "marks", "last_seen_place", "clothing", "language_spoken")
schema_fields = {("language" if field == "language_spoken" else field): field for field in fields}
aliases = {}
for field, heading in [("name", "Fixed name aliases"), ("last_seen_place", "Fixed place aliases")]:
    section = prereg.read_text().split(heading, 1)[1].split("\n\n", 1)[0]
    entries = [line[2:].split(", ") for line in section.splitlines() if line.startswith("- ")]
    assert entries
    aliases[field] = {v.casefold(): row[0].casefold() for row in entries for v in row}
patterns = {
    field: re.compile(
        r"(?<!\S)(?:"
        + "|".join(map(re.escape, sorted(values, key=lambda x: (-len(x), x))))
        + r")(?!\S)"
    )
    for field, values in aliases.items()
}


def norm(field, value):
    value = " ".join(
        "".join(
            " " if unicodedata.category(ch).startswith("P") else ch
            for ch in unicodedata.normalize("NFC", value).casefold()
        ).split()
    )
    if field in patterns:
        value = patterns[field].sub(lambda m: aliases[field][m[0]], value)
    if field == "age":
        match = re.fullmatch(r"(\d+)(?: years?(?: old)?)?", value)
        if match:
            value = str(int(match[1]))
    if field == "gender":
        value = {"woman": "female", "girl": "female", "man": "male", "boy": "male"}.get(
            value, value
        )
    return value


def score(item, text, extraction):
    kept, dropped = ground(text, extraction)
    predicted = collections.defaultdict(set)
    for entry in kept:
        if entry.name in schema_fields:
            field = schema_fields[entry.name]
            predicted[field].add(norm(field, entry.value))
    counts = {}
    for schema, field in schema_fields.items():
        label = item["expected"][field]
        expected = norm(field, label["value"]) if label else ""
        counts[field] = dict(
            expected=int(bool(expected)),
            predicted=len(predicted[field]),
            correct=int(bool(expected) and expected in predicted[field]),
            quote_drops=sum(
                x.name == schema and not is_grounded(x.evidence, text) for x in dropped
            ),
            blank_drops=sum(x.name == schema and is_grounded(x.evidence, text) for x in dropped),
        )
    return counts


async def extract_detail(llm, resources, item, source, lang):
    model = None
    try:
        result = await llm.run(
            "turn", resources.messages(source, {}, None), schema_model=Extraction, lang=lang
        )
        model = result.model
        extraction = result.parsed
        status = "ok" if extraction is not None else "missing_extraction"
        trail, attempts = result.trail, result.attempts
    except LLMUnavailable as exc:
        status = "model_unavailable"
        extraction = None
        trail, attempts = exc.trail, exc.attempts
    return extraction_detail(item, source, status, model, extraction, trail, attempts)


def extraction_detail(item, source, status, model, extraction, trail, attempts):
    ex = extraction or Extraction(intent="other")
    return dict(
        status=status,
        model=model,
        fields=score(item, source, ex),
        kept_extraction=ex.model_dump(),
        trail=trail,
        attempts=attempts,
    )


def write_detail(handle, record):
    handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    handle.flush()


class Cap(Exception):
    pass


async def run():
    cfg = get_settings()
    models = cfg.models()
    client = OllamaClient(cfg.ollama_base, cfg.ollama_key.get_secret_value())
    caps = Capabilities(client, models)
    resources = Resources()
    llm = LLM(client, models, capabilities=caps)
    attempts = 0
    calls = 0

    async def count(request):
        nonlocal attempts
        if request.url.path == "/api/chat":
            if attempts >= args.cap:
                raise Cap
            attempts += 1

    client._c.event_hooks["request"].append(count)

    async def extract(clip, side):
        nonlocal calls
        if calls >= args.cap or attempts >= args.cap:
            raise Cap
        calls += 1
        item = items[clip["item_id"]]
        source = item["text"] if side == "reference" else clip["transcript"]
        lang = "hi" if clip["lang"] == "hinglish" else clip["lang"]
        return await extract_detail(llm, resources, item, source, lang)

    async def pair(clip):
        a = await extract(clip, "reference")
        b = await extract(clip, "transcript")
        return dict(
            item_id=clip["item_id"],
            lang=clip["lang"],
            category=clip["category"],
            reference=a,
            transcript=b,
        )

    pairs = []
    try:
        await caps.probe()
        print("Preregistration SHA-256", digest, flush=True)
        print("Production model availability probe complete", flush=True)
        with args.detail.open("x") as f:
            for i in range(0, len(clips), 5):
                batch = await asyncio.gather(
                    *(pair(clip) for clip in clips[i : i + 5]), return_exceptions=True
                )
                for result in batch:
                    if isinstance(result, Exception):
                        continue
                    write_detail(f, result)
                    pairs.append(result)
                f.flush()
                errors = [x for x in batch if isinstance(x, Exception)]
                if errors:
                    print(
                        "Stopped:",
                        collections.Counter(type(x).__name__ for x in errors),
                        flush=True,
                    )
                    break
                if len(pairs) % 20 == 0 or len(pairs) == len(clips):
                    print(
                        f"Completed {len(pairs)} pairs, {calls} extractions, {attempts} provider attempts",
                        flush=True,
                    )
    finally:
        await client.aclose()
    return pairs, calls, attempts


def report(pairs, calls, attempts):
    def sums(group, side, fs):
        return collections.Counter(
            {
                key: sum(p[side]["fields"][f][key] for p in group for f in fs)
                for key in ("expected", "predicted", "correct", "quote_drops", "blank_drops")
            }
        )

    def ratio(a, b):
        return a / b if b else None

    def pct(v):
        return "unavailable" if v is None else f"{v:.2%}"

    def delta(a, b):
        return "unavailable" if a is None or b is None else f"{100 * (b - a):+.2f} pp"

    def summary(label, group, fs=fields):
        a, b = [sums(group, side, fs) for side in ("reference", "transcript")]
        ar, br = [ratio(c["correct"], c["expected"]) for c in (a, b)]
        ap, bp = [ratio(c["correct"], c["predicted"]) for c in (a, b)]
        return (
            f"- {label} · n={len(group)} · reference recall {pct(ar)} ({a['correct']}/{a['expected']}), precision {pct(ap)} ({a['correct']}/{a['predicted']})"
            f" · transcript recall {pct(br)} ({b['correct']}/{b['expected']}), precision {pct(bp)} ({b['correct']}/{b['predicted']})"
            f" · Δ recall {delta(ar, br)}, Δ precision {delta(ap, bp)} · quote drops {a['quote_drops']}/{b['quote_drops']} (reference/transcript) · blank drops {a['blank_drops']}/{b['blank_drops']}"
        )

    lines = [
        "# Synthetic speech field recovery",
        "",
        f"Preregistration SHA-256 `{digest}`.",
        "",
        f"{len(pairs)} of {len(clips)} complete pairs. {calls} extraction invocations and {attempts} Ollama chat attempts. 0 Gnani requests.",
        "The durable intake turn ran with an empty draft, no current question, and production model routing, prompt, schema and grounding. The local Redis usage ledger was unavailable. The run enforced an independent hard cap on invocations and provider attempts.",
        "Reference labels are draft_unverified. The speech is Sarvam-generated, so results describe the pipeline on synthetic speech only. Cell sizes are small. The alias list affects the result and was fixed before scoring.",
        "Differences are transcript minus reference. Provider failures in completed pairs count as zero recovery and zero predictions.",
        "",
        summary("Overall", pairs),
    ]
    for title, field in [("By language", "lang"), ("By category", "category")]:
        lines += ["", f"## {title}", ""]
        lines.extend(
            summary(key, [p for p in pairs if p[field] == key])
            for key in sorted({c[field] for c in clips})
        )
    lines += ["", "## By field", ""]
    lines.extend(summary(f, pairs, (f,)) for f in fields)
    ranking = []
    for pair in pairs:
        a, b = [sums([pair], side, fields) for side in ("reference", "transcript")]
        if a["expected"]:
            ranking.append(((a["correct"] - b["correct"]) / a["expected"], pair["item_id"]))
    lines += ["", "## Five largest recall drops", ""]
    lines.extend(
        f"- {item} · {100 * value:.2f} pp"
        for value, item in sorted(ranking, key=lambda x: (-x[0], x[1]))[:5]
    )
    lines += ["", "## Extraction outcomes", ""]
    for side in ("reference", "transcript"):
        statuses = collections.Counter(p[side]["status"] for p in pairs)
        lines.append(
            f"- {side} · " + (", ".join(f"{key} {n}" for key, n in sorted(statuses.items())) or "0")
        )
    if len(pairs) < len(clips):
        lines += ["", "The run is partial. Aggregate scores use complete pairs only."]
    return lines


def classify(field, expected, values, matched):
    if matched:
        return "matched"
    if not values:
        return "extraction omitted"
    if field == "age":
        expected_numbers = set(re.findall(r"\d+", expected))
        wording = r"\b(?:about|around|approximately|aged?|years?|months?|between|to|yrs?|old)\b"
        for value in values:
            numbers = set(re.findall(r"\d+", value))
            if expected_numbers & numbers and (
                len(numbers) > 1
                or len(expected_numbers) > 1
                or re.search(wording, value, re.I)
                or re.search(wording, expected, re.I)
            ):
                return "format"
    if field == "language_spoken":
        for value in values:
            clean = re.sub(
                r"\b(?:speaks?|spoken|language|languages|speaker)\b", "", value, flags=re.I
            )
            if norm(field, clean) == norm(field, expected):
                return "format"
    return "wrong value"


def display(value):
    # Show only bounded field values. Suppress digit strings that could be identifiers.
    if not value:
        return "—"
    if len(value) > 80 or len(re.sub(r"\D", "", value)) >= 8 or "@" in value:
        return "[redacted]"
    return " ".join(value.split()).replace("`", "")


def replay():
    pairs = jsonl(args.detail)
    if not pairs or any(
        not isinstance(p.get(side, {}).get("kept_extraction", {}).get("fields"), list)
        or any("value" not in field for field in p[side]["kept_extraction"]["fields"])
        for p in pairs
        for side in ("reference", "transcript")
    ):
        raise SystemExit("Saved detail lacks extracted field values. No extraction was run.")
    saved = (out / "field_recovery.md").read_text().splitlines()
    run_line = next(line for line in saved if " Ollama chat attempts." in line)
    counts = re.search(r"(\d+) extraction invocations and (\d+) Ollama chat attempts", run_line)
    calls, attempts = map(int, counts.groups())
    if attempts > args.cap:
        raise SystemExit("Saved run exceeds the supplied cap.")
    clips_by_id = {clip["item_id"]: clip for clip in clips}
    grounded = {}
    for p in pairs:
        item = items[p["item_id"]]
        for side in ("reference", "transcript"):
            text = item["text"] if side == "reference" else clips_by_id[p["item_id"]]["transcript"]
            ex = Extraction.model_validate(p[side]["kept_extraction"])
            actual = score(item, text, ex)
            if actual != p[side]["fields"]:
                raise SystemExit("Replayed grounding or scoring differs from saved detail.")
            grounded[p["item_id"], side] = ground(text, ex)[0]
    lines = report(pairs, calls, attempts)
    metrics = [line for line in lines if line.startswith("- ") or line == run_line]
    if not all(line in saved for line in metrics):
        raise SystemExit("Replayed aggregates differ from the saved report.")

    # Model names on completed results can identify final choices only.
    import yaml

    models = yaml.safe_load((backend / "config/models.yaml").read_text())
    routing = LLM(None, models)
    model_results = collections.Counter()
    different_final_ids = collections.defaultdict(list)
    for p in pairs:
        lang = "hi" if p["lang"] == "hinglish" else p["lang"]
        primary = routing.chain("turn", lang)[0]
        for side in ("reference", "transcript"):
            final = p[side]["model"]
            key = (
                "primary"
                if final == primary
                else "different final model"
                if final
                else "unavailable"
            )
            model_results[side, key] += 1
            if key == "different final model":
                different_final_ids[side].append(p["item_id"])

    diagnostic = [
        "# Field recovery diagnostic",
        "",
        f"- Replayed {len(pairs)} pairs and matched {len(metrics)} published result lines.",
        "- Requests sent during replay: 0.",
        "- Quote grounding drops: 0 on references and 0 on transcripts. These are measured counts. The replay ran production `ground` on the original inputs and saved schema outputs, then checked dropped evidence with `is_grounded`.",
        f"- Model attempt split: unavailable for the {attempts} Ollama attempts. The saved detail records only the final model for each completed extraction. It lacks per-attempt models, retry and fallback traces, and partial pairs.",
        *[
            f"- {side} completed final models · primary {model_results[side, 'primary']} · different final model {model_results[side, 'different final model']} · unavailable {model_results[side, 'unavailable']}."
            for side in ("reference", "transcript")
        ],
        *[
            f"- {side} cases ending on a different model · {', '.join(sorted(different_final_ids[side])) or 'none'}."
            for side in ("reference", "transcript")
        ],
        "- Redis usage reservation fails closed for that provider attempt. In `app/llm.py` the reservation precedes the provider call and is outside its retry handler.",
        "",
        '`day = await self.usage.reserve(role) if self.usage else ""`',
        "",
        "Production supplies a usage ledger. A Redis error from reservation propagates before the provider call. The offline evaluation had no ledger and used its separate cap.",
        "",
        "Sample selection uses item ID order among completed pairs with the expected field present. Each row shows expected, grounded extracted values, and preregistered match for both conditions.",
    ]
    for field, schema, count in [("age", "age", 20), ("language_spoken", "language", 15)]:
        sample = [
            p
            for p in sorted(pairs, key=lambda p: p["item_id"])
            if p["reference"]["fields"][field]["expected"]
        ][:count]
        diagnostic += ["", f"## {field} ({len(sample)} pairs)", ""]
        categories = collections.Counter()
        for p in sample:
            item_id = p["item_id"]
            expected = items[item_id]["expected"][field]["value"]
            line = f"- {item_id} · expected {display(expected)}"
            for side in ("reference", "transcript"):
                values = [f.value for f in grounded[item_id, side] if f.name == schema]
                matched = bool(p[side]["fields"][field]["correct"])
                kind = classify(field, expected, values, matched)
                categories[side, kind] += 1
                line += f" · {side} {', '.join(map(display, values)) or '—'} ({kind})"
            diagnostic.append(line)
        diagnostic += [
            "",
            *[f"- {side} · {kind} {n}" for (side, kind), n in sorted(categories.items())],
        ]
    path = out / "field_diagnostic.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(diagnostic) + "\n")
    for line in diagnostic:
        if line.startswith("- ") and not re.match(r"- [a-z]+-\d+ ", line):
            print(line)


def main():
    global args, items, clips
    parser = argparse.ArgumentParser(
        description="Replay or run the paired field recovery evaluation."
    )
    parser.add_argument("--items", required=True, type=Path)
    parser.add_argument(
        "--detail",
        default=out / "field_recovery_detail.jsonl",
        type=Path,
        help="Saved detail for replay or new output for --run",
    )
    parser.add_argument("--cap", required=True, type=int)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--replay", action="store_true")
    mode.add_argument("--run", action="store_true")
    args = parser.parse_args()
    if not 1 <= args.cap <= 282:
        parser.error("--cap must be between 1 and 282")

    items = {r["item_id"]: r for r in jsonl(args.items)}
    clips = jsonl(out / "transcripts.jsonl")
    assert len(clips) == len({r["item_id"] for r in clips}) == 141
    assert all(
        r["status"] == "ok"
        and r["lang"] == items[r["item_id"]]["lang"]
        and r["category"] == items[r["item_id"]]["category"]
        for r in clips
    )
    if args.replay:
        replay()
    else:
        if args.detail.exists():
            parser.error("--detail already exists")
        if 2 * len(clips) > args.cap:
            parser.error("planned extraction count exceeds the cap")
        result = report(*asyncio.run(run()))
        print("\n".join(result))


if __name__ == "__main__":
    main()
