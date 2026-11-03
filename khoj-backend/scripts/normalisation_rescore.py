"""Rescore saved speech extraction results without contacting providers."""

import argparse
import hashlib
import json
import re
import unicodedata
from pathlib import Path

from app.schemas import Extraction, ground

OUT = Path(__file__).resolve().parents[2] / "artifacts/speech-eval"
FIELDS = {"age": "age", "language_spoken": "language"}
SIDES = ("reference", "transcript")
LANGUAGES = {
    alias.casefold(): aliases.split("/")[0]
    for aliases in (
        "Bengali/বাংলা",
        "Marathi/मराठी",
        "Hindi/हिंदी/हिन्दी",
        "Kannada/ಕನ್ನಡ",
        "Tamil/தமிழ்",
        "Telugu/తెలుగు",
        "Malayalam/മലയാളം",
        "Gujarati/ગુજરાતી",
        "Punjabi/ਪੰਜਾਬੀ",
        "English",
    )
    for alias in aliases.split("/")
}


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def normalise(field, value):
    value = unicodedata.normalize("NFC", value).casefold().strip()
    if field == "language_spoken":
        return LANGUAGES.get(value)
    value = re.sub(r"\(\s*(?:approximate|corrected)\s*\)", "", value)
    value = re.sub(r"\b(?:about|approximately|approx\.?|years old|years|yrs|saal)\b", "", value)
    value = value.strip()
    if re.fullmatch(r"\d+", value):
        return int(value)
    match = re.fullmatch(r"(\d+)\s*(?:-|–|—|to)\s*(\d+)", value)
    return tuple(map(int, match.groups())) if match else None


def matches(field, expected, prediction):
    if field == "age" and isinstance(expected, tuple):
        return isinstance(prediction, int) and expected[0] <= prediction <= expected[1]
    return prediction is not None and prediction == expected


def corrected_counts(field, expected, kept):
    canonical_expected = normalise(field, expected)
    values = {entry.value for entry in kept if entry.name == FIELDS[field]}
    predictions = {
        value if (canonical := normalise(field, value)) is None else canonical for value in values
    }
    return {
        "predicted": len(predictions),
        "correct": int(any(matches(field, canonical_expected, value) for value in predictions)),
    }


def diagnostic_ids(path):
    contents = path.read_text()
    return {
        field: set(re.findall(r"^- ([a-z]+-\d+) ·", section, re.M))
        for field, section in (
            (field, contents.split(f"## {field} (", 1)[1].split("\n## ", 1)[0]) for field in FIELDS
        )
    }


def native_count(items, field):
    scripts = (
        "DEVANAGARI",
        "BENGALI",
        "KANNADA",
        "TAMIL",
        "TELUGU",
        "MALAYALAM",
        "GUJARATI",
        "GURMUKHI",
    )
    return sum(
        any(unicodedata.name(ch, "").startswith(scripts) for ch in label["value"])
        for item in items.values()
        if (label := item["expected"][field])
    )


def metric(correct, denominator):
    return (
        f"{correct / denominator:.2%} ({correct}/{denominator})"
        if denominator
        else "unavailable (0/0)"
    )


def summary(rows):
    for field in FIELDS:
        test = [row for row in rows if row["field"] == field and row["split"] == "test"]
        yield f"## {field} test set"
        yield ""
        for side in SIDES:
            condition = [row for row in test if row["condition"] == side]
            groups = [("Overall", condition)]
            for key in ("lang", "category"):
                groups.extend(
                    (f"{key}={value}", [row for row in condition if row[key] == value])
                    for value in sorted({row[key] for row in condition})
                )
            for label, group in groups:
                scores = []
                for version in ("original", "corrected"):
                    correct = sum(row[version]["correct"] for row in group)
                    predicted = sum(row[version]["predicted"] for row in group)
                    scores.append(
                        f"{version} recall {metric(correct, len(group))}, "
                        f"precision {metric(correct, predicted)}"
                    )
                yield f"- {side}, {label}, n={len(group)}. " + " · ".join(scores)
        yield ""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--items", required=True, type=Path)
    args = parser.parse_args()
    items = {row["item_id"]: row for row in read_jsonl(args.items)}
    clips = {row["item_id"]: row for row in read_jsonl(OUT / "transcripts.jsonl")}
    pairs = read_jsonl(OUT / "field_recovery_detail.jsonl")
    dev = diagnostic_ids(OUT / "field_diagnostic.md")
    assert [len(dev[field]) for field in FIELDS] == [20, 15]
    rows = []
    for pair in pairs:
        item_id = pair["item_id"]
        item = items[item_id]
        for side in SIDES:
            saved = pair[side]
            source = item["text"] if side == "reference" else clips[item_id]["transcript"]
            kept, _ = ground(source, Extraction.model_validate(saved["kept_extraction"]))
            for field in FIELDS:
                original = saved["fields"][field]
                label = item["expected"][field]
                assert bool(original["expected"]) == bool(label)
                if label:
                    rows.append(
                        dict(
                            item_id=item_id,
                            lang=pair["lang"],
                            category=pair["category"],
                            field=field,
                            condition=side,
                            split="development" if item_id in dev[field] else "test",
                            original={key: original[key] for key in ("predicted", "correct")},
                            corrected=corrected_counts(field, label["value"], kept),
                        )
                    )

    for field in FIELDS:
        assert {
            row["item_id"]
            for row in rows
            if row["field"] == field and row["split"] == "development"
        } == dev[field]
    assert normalise("age", "about 77 years old (approximate)") == 77
    assert matches("age", normalise("age", "78–80 years"), 78)
    assert not matches("age", 78, 77)
    assert normalise("language_spoken", "हिन्दी") == "Hindi"
    assert corrected_counts("age", "78", []) == {"predicted": 0, "correct": 0}
    reference_misses = [
        row
        for row in rows
        if row["field"] == "language_spoken"
        and row["condition"] == "reference"
        and not row["original"]["correct"]
    ]
    assert len(reference_misses) == 8
    resolved = [row["item_id"] for row in reference_misses if row["corrected"]["correct"]]
    for item_id, field in (("en-002", "language_spoken"), ("bn-009", "age")):
        row = next(
            row
            for row in rows
            if row["item_id"] == item_id
            and row["field"] == field
            and row["condition"] == "transcript"
        )
        assert not row["corrected"]["correct"]

    digest = hashlib.sha256((OUT / "normalisation_preregistration.md").read_bytes()).hexdigest()
    lines = [
        "# Age and language normalisation rescore",
        "",
        f"Preregistration SHA-256 `{digest}`.",
        "",
        "Zero provider requests. Development pairs are excluded separately by field.",
        f"{len(resolved)} of 8 reference language mismatches resolve ({', '.join(sorted(resolved))}).",
        "en-002 remains a transcript-side language omission. bn-009 remains a transcript-side age mismatch.",
        "",
        "## Native-script expected labels across the source corpus",
        "",
        *[
            f"- {field}. {native_count(items, field)} of {sum(bool(item['expected'][field]) for item in items.values())}."
            for field in next(iter(items.values()))["expected"]
        ],
        "",
        *summary(rows),
    ]
    (OUT / "normalisation_rescore.md").write_text("\n".join(lines) + "\n")
    (OUT / "normalisation_rescore_detail.jsonl").write_text(
        "".join(json.dumps(row) + "\n" for row in rows)
    )


if __name__ == "__main__":
    main()
