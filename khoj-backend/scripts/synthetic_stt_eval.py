"""Replay the synthetic STT scores and diagnose script mismatch offline."""

import argparse
import collections
import csv
import json
import statistics
import unicodedata
from pathlib import Path


def norm(text):
    return " ".join(
        "".join(
            " "
            if unicodedata.category(ch).startswith("P")
            else ch.lower()
            if unicodedata.name(ch, "").startswith("LATIN ")
            else ch
            for ch in unicodedata.normalize("NFC", text)
        ).split()
    )


def distance(ref, hyp):
    prev = list(range(len(hyp) + 1))
    for i, a in enumerate(ref, 1):
        row = [i]
        for j, b in enumerate(hyp, 1):
            row.append(min(prev[j] + 1, row[-1] + 1, prev[j - 1] + (a != b)))
        prev = row
    return prev[-1]


def script(text):
    names = {unicodedata.name(ch, "").split(" ", 1)[0] for ch in text if ch.isalpha()}
    if {"LATIN", "DEVANAGARI"} <= names:
        return "Mixed"
    if "DEVANAGARI" in names:
        return "Devanagari only"
    if "LATIN" in names:
        return "Latin only"
    return "Neither"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--items", required=True, type=Path)
    parser.add_argument("--write-diagnostic", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    prepared = root / "output/audio_prepared"
    artifacts = root / "artifacts/speech-eval"
    with (prepared / "segments.csv").open(newline="") as handle:
        eligible = {
            Path(row["prepared_file"]).name: row["item_id"]
            for row in csv.DictReader(handle)
            if row["scored"] == "true"
        }
    with args.items.open() as handle:
        refs = {row["item_id"]: row for row in map(json.loads, handle)}
    with (artifacts / "transcripts.jsonl").open() as handle:
        rows = list(map(json.loads, handle))
    if len(rows) != len(eligible) or {r["clip_id"]: r["item_id"] for r in rows} != eligible:
        raise SystemExit("Saved transcript coverage differs from the prepared scored set.")
    failed = collections.defaultdict(list)
    metrics = []
    for row in rows:
        if row["status"] == "failed":
            failed[row["error_kind"]].append(row["item_id"])
            continue
        ref = norm(refs[row["item_id"]]["text"])
        hyp = norm(row["transcript"])
        assert ref and ref.split()
        metrics.append(
            (
                row,
                distance(ref.split(), hyp.split()),
                len(ref.split()),
                distance(ref, hyp),
                len(ref),
            )
        )

    def totals(group):
        if not group:
            return "n=0 · WER unavailable · CER unavailable"
        _, we, w, ce, c = zip(*group, strict=True)
        return f"n={len(group)} · WER {sum(we) / sum(w):.2%} · CER {sum(ce) / sum(c):.2%}"

    report = (artifacts / "wer_report.md").read_text().splitlines()
    expected = {f"- Overall · {totals(metrics)}"}
    expected.add(
        f"- Median per-clip WER {statistics.median(x[1] / x[2] for x in metrics):.2%} · median per-clip CER {statistics.median(x[3] / x[4] for x in metrics):.2%}."
    )
    for fields in [("lang",), ("category",), ("lang", "category")]:
        groups = collections.defaultdict(list)
        counts = collections.Counter(tuple(r[f] for f in fields) for r in rows)
        for entry in metrics:
            groups[tuple(entry[0][f] for f in fields)].append(entry)
        expected.update(
            f"- {' / '.join(k)} · {totals(groups[k])} · eligible {n}" for k, n in counts.items()
        )
    for row, edits, words, char_edits, chars in sorted(
        metrics, key=lambda x: (-x[1] / x[2], x[0]["item_id"])
    )[:5]:
        expected.add(f"- {row['item_id']} · WER {edits / words:.2%} · CER {char_edits / chars:.2%}")
    if not expected.issubset(report):
        raise SystemExit("Replayed metric lines differ from the existing report.")
    print(f"Reproduced {len(expected)} published metric lines. {totals(metrics)}")
    lines = ["# Synthetic Hinglish script diagnostic", ""]
    for lang in ("hinglish", "hi"):
        subset = [x for x in metrics if x[0]["lang"] == lang]
        counts = collections.Counter(script(x[0]["transcript"]) for x in subset)
        lines.append(
            f"- {lang} · {len(subset)} hypotheses · Latin only {counts['Latin only']} · Devanagari only {counts['Devanagari only']} · mixed {counts['Mixed']} · neither {counts['Neither']} · any Devanagari {counts['Devanagari only'] + counts['Mixed']}."
        )
    hinglish = [x for x in metrics if x[0]["lang"] == "hinglish"]
    latin = [x for x in hinglish if script(x[0]["transcript"]) == "Latin only"]
    deva = [x for x in hinglish if script(x[0]["transcript"]) in {"Devanagari only", "Mixed"}]
    ref_scripts = collections.Counter(script(refs[x[0]["item_id"]]["text"]) for x in hinglish)
    deva_tokens = sum(
        script(word) in {"Devanagari only", "Mixed"}
        for entry in hinglish
        for word in norm(entry[0]["transcript"]).split()
    )
    word_edits = sum(entry[1] for entry in hinglish)
    lines += [
        f"- Hinglish Latin-only reference count · {ref_scripts['Latin only']} of {len(hinglish)}.",
        f"- Hinglish Latin-only hypotheses · {totals(latin)}.",
        f"- Hinglish hypotheses containing Devanagari · {totals(deva)}.",
        f"- Hinglish word edits from hypotheses containing Devanagari · {sum(x[1] for x in deva)} of {sum(x[1] for x in hinglish)}. Their references account for {sum(x[2] for x in deva)} of {sum(x[2] for x in hinglish)} words.",
        "",
        f"- {deva_tokens} hypothesis word tokens contain Devanagari. Against Latin-only references, each must be inserted or substituted in any word alignment. This accounts for at least {deva_tokens / word_edits:.2%} of the {word_edits} edits under exact matching.",
        "",
        "Script mismatch dominates exact matching on this set. This bound does not estimate how many edits transliteration would remove, because the same tokens may also contain recognition errors.",
        "",
        "Options include fixed Devanagari-to-Latin ITRANS, ISO 15919, or a predefined Roman Hindi alias list. If asked to write a rule before scoring, I would preregister fixed ITRANS for Devanagari spans and preserve the original script-sensitive baseline. Roman Hindi spelling variants would still need separate treatment.",
    ]
    diagnostic = "\n".join(lines) + "\n"
    print(diagnostic, end="")
    if args.write_diagnostic:
        (artifacts / "hinglish_script_check.md").write_text(diagnostic)


if __name__ == "__main__":
    main()
