"""Frozen label scoring shared by evaluation and paired thinking experiments."""

import re
from collections import Counter, defaultdict

CATEGORY_MAP = {
    "clean": "clean_single_language",
    "correction": "corrections",
    "ambiguous_name": "conflicting_values",
    "conflicting_values": "conflicting_values",
    "stt_noise": "stt_errors",
    "injection": "injection_attempts",
    "rambling": "long_rambling",
    "hinglish": "hinglish",
}
CATEGORIES = (
    "clean_single_language",
    "hinglish",
    "long_rambling",
    "corrections",
    "conflicting_values",
    "stt_errors",
    "injection_attempts",
)


def categories(row):
    result = []
    category = CATEGORY_MAP.get(row["category"])
    if category == "clean_single_language" and row["lang"] == "hinglish":
        category = None
    if category:
        result.append(category)
    if row["lang"] == "hinglish" and "hinglish" not in result:
        result.append("hinglish")
    return result


def norm(value):
    value = re.sub(r"\b(years? old|years?|yrs?)\b", "", value.casefold())
    return re.sub(r"[^\w]+", " ", value).strip()


def pairs(fields):
    return {(f["name"], norm(f["value"])) for f in fields}


def score(row, raw_fields, kept_fields, failure=None):
    expected = pairs(row["expected_fields"])
    aliases = {
        (field["name"], norm(alias)): (field["name"], norm(field["value"]))
        for field in row["expected_fields"]
        for alias in field.get("aliases", [])
    }
    raw = {aliases.get(pair, pair) for pair in pairs(raw_fields)}
    actual = {aliases.get(pair, pair) for pair in pairs(kept_fields)}
    return {
        "case": row["id"],
        "lang": row["lang"],
        "categories": categories(row),
        "split": row.get("split", "legacy_development"),
        "tp": len(actual & expected),
        "fp": len(actual - expected),
        "fn": len(expected - actual),
        "raw_fp": len(raw - expected),
        "raw_total": len(raw),
        "kept_total": len(actual),
        "expected_count": len(expected),
        "failure": failure,
        "extra": sorted(actual - expected),
        "missing": sorted(expected - actual),
        "expected": row["expected_fields"],
        "kept": kept_fields,
        "correct_abstention": not expected and not actual and failure is None,
    }


def summarize(records):
    if not records:
        return None
    totals = {
        key: sum(r[key] for r in records)
        for key in ("tp", "fp", "fn", "raw_fp", "raw_total", "kept_total", "expected_count")
    }
    tp, fp, fn = totals["tp"], totals["fp"], totals["fn"]
    empty = [r for r in records if r["expected_count"] == 0]
    return {
        "cases": len(records),
        **totals,
        "precision": tp / (tp + fp) if tp + fp else None,
        "recall": tp / (tp + fn) if tp + fn else None,
        "f1": 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else None,
        "hallucination_count": fp,
        "kept_hallucination_rate": fp / totals["kept_total"] if totals["kept_total"] else 0,
        "failures": sum(r["failure"] is not None for r in records),
        "abstention_cases": len(empty),
        "correct_abstentions": sum(r["correct_abstention"] for r in empty),
    }


def breakdown(records):
    by_language = defaultdict(list)
    by_category = defaultdict(list)
    by_split = defaultdict(list)
    for row in records:
        by_language[row["lang"]].append(row)
        by_split[row["split"]].append(row)
        for category in row["categories"]:
            by_category[category].append(row)
    return {
        "overall": summarize(records),
        "by_language": {k: summarize(v) for k, v in sorted(by_language.items())},
        "by_category": {k: summarize(v) for k, v in sorted(by_category.items())},
        "by_category_language": {
            category: {
                lang: summarize([r for r in rows if r["lang"] == lang])
                for lang in sorted({r["lang"] for r in rows})
            }
            for category, rows in sorted(by_category.items())
        },
        "by_split": {k: summarize(v) for k, v in sorted(by_split.items())},
    }


def counts(rows):
    values = Counter(category for row in rows for category in categories(row))
    return {category: values[category] for category in CATEGORIES}
