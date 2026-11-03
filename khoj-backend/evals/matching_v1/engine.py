"""Offline missing-to-found ranking and evaluation."""

import argparse
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

from .generator import CORE_DISTRACTORS, Report, generate

SIGNAL_KEYS = frozenset(
    {
        "name_exact",
        "name_one_token",
        "sex",
        "age_overlap",
        "height_close",
        "build",
        "complexion",
        "hair",
        "upper_dress",
        "lower_dress",
        "marks_overlap",
        "same_station",
        "same_place",
        "date_close",
    }
)


def age_bounds(value: str) -> tuple[int, int]:
    start, _, end = value.partition("-")
    return int(start), int(end or start)


def report_name(description: str) -> str:
    prefix = "Name reported as "
    if not description.startswith(prefix):
        return ""
    return description[len(prefix) :].split(".", 1)[0].casefold()


def score(query: Report, candidate: Report) -> tuple[int, tuple[str, ...]]:
    a, b = query.fields, candidate.fields
    signals = {}

    left, right = (report_name(row["description"]) for row in (a, b))
    if left and right:
        if left == right:
            signals["name_exact"] = 32
        elif left.split()[0] == right.split()[0]:
            signals["name_one_token"] = 12
    low_a, high_a = age_bounds(a["age"])
    low_b, high_b = age_bounds(b["age"])
    if max(low_a, low_b) <= min(high_a, high_b):
        signals["age_overlap"] = 13
    if abs(int(a["height"]) - int(b["height"])) <= 4:
        signals["height_close"] = 10
    marks_a, marks_b = (set(row["physical_details"].split("; ")) - {""} for row in (a, b))
    if overlap := marks_a & marks_b:
        signals["marks_overlap"] = min(len(overlap), 2) * 9
    if abs((date.fromisoformat(a["dd_date"]) - date.fromisoformat(b["dd_date"])).days) <= 3:
        signals["date_close"] = 6
    for field, key, points in (
        ("sex", "sex", 5),
        ("build", "build", 4),
        ("complexion", "complexion", 3),
        ("hair", "hair", 4),
        ("upper_dress", "upper_dress", 5),
        ("lower_dress", "lower_dress", 5),
        ("police_station", "same_station", 3),
        ("place_of_missing", "same_place", 5),
    ):
        if a[field] and a[field].casefold() == b[field].casefold():
            signals[key] = points
    return sum(signals.values()), tuple(signals)


def band(points: int) -> str:
    if points >= 62:
        return "Strong"
    if points >= 37:
        return "Possible"
    return "Weak"


class Index:
    def __init__(self, reports: list[Report]):
        self.blocks = defaultdict(list)
        for report in reports:
            self.blocks[report.fields["state"], report.kind].append(report)

    def rank(self, query: Report) -> list[tuple[str, int, str, tuple[str, ...]]]:
        if query.kind != "missing":
            raise ValueError("Queries must be missing reports")
        ranked = []
        for candidate in self.blocks[query.fields["state"], "found"]:
            points, reasons = score(query, candidate)
            ranked.append((candidate.item_id, points, band(points), reasons))
        return sorted(ranked, key=lambda row: (-row[1], row[0]))


def evaluate(missing, indexed, truth, distractor_ids):
    index = Index(indexed)
    pairs = {pair.missing_id: pair for pair in truth}
    ranks = Counter()
    hits = Counter()
    totals = Counter()
    bands = Counter()
    strong_true = 0
    strong_distractor_links = 0
    strong_distractors = set()
    reasons_valid = True
    for query in missing:
        pair = pairs[query.item_id]
        ranking = index.rank(query)
        ranks_by_id = {row[0]: rank for rank, row in enumerate(ranking, 1)}
        rank = ranks_by_id.get(pair.found_id)
        ranks[rank] += 1
        totals[pair.noise] += 1
        hits[pair.noise] += rank is not None and rank <= 5
        for ident, _, strength, reasons in ranking:
            reasons_valid &= set(reasons) <= SIGNAL_KEYS
            bands[strength] += 1
            if strength == "Strong":
                strong_true += ident == pair.found_id
                if ident in distractor_ids:
                    strong_distractor_links += 1
                    strong_distractors.add(ident)
    return (
        ranks,
        hits,
        totals,
        bands,
        strong_true,
        strong_distractor_links,
        strong_distractors,
        reasons_valid,
    )


def report() -> str:
    missing, found, distractors, truth = generate()
    lines = [
        "# Matching prototype v1",
        "",
        "Seed 20261103. The prototype ranks found reports for each missing query. It uses fictional data and deterministic scoring.",
        "",
        "The requested 50 two-record pairs and 150 distractors imply 250 records. The 200-record core uses the first 100 distractors. The 250-record stress run adds the remaining 50. Both use the same 50 queries and true matches.",
        "",
        "Distractors copy one or two fields from a fixed set of six identity or location fields of an anchor report. Their state is shared for blocking. Other independently generated attributes can coincide.",
        "",
        "Blocking uses state and the found record kind. Scores are additive, with ties broken by ascending fictional ID. Strong begins at 62 points and Possible at 37. Strong precision includes every Strong query-candidate link. The rank histogram tracks the true found report.",
        "",
        "| Corpus | Noise | Recall@5 |",
        "|---|---|---:|",
    ]
    extras = []
    for label, population in (("Core", distractors[:CORE_DISTRACTORS]), ("Stress", distractors)):
        ranks, hits, totals, bands, true, false_d, strong_d, valid = evaluate(
            missing, found + population, truth, {row.item_id for row in population}
        )
        overall = sum(hits.values()) / len(truth)
        for noise in ("Overall", "none", "one", "two or more"):
            numerator, denominator = (
                (sum(hits.values()), len(truth))
                if noise == "Overall"
                else (hits[noise], totals[noise])
            )
            lines.append(
                f"| {label} | {noise} | {numerator}/{denominator} ({numerator / denominator:.2%}) |"
            )
        strong = bands["Strong"]
        precision = f"{true}/{strong} ({true / strong:.2%})" if strong else "unavailable (0/0)"
        histogram = ", ".join(
            f"{rank} → {n}" for rank, n in sorted(ranks.items(), key=lambda row: row[0] or 999)
        )
        extras += [
            "",
            f"## {label}",
            "",
            f"- Records {len(missing) + len(found) + len(population)}. Queries {len(missing)}. Indexed found reports {len(found) + len(population)}.",
            f"- Strong precision {precision}. Distractors reaching Strong {len(strong_d)} ({false_d} links).",
            f"- Candidate bands. Strong {strong}, Possible {bands['Possible']}, Weak {bands['Weak']}.",
            f"- True-match rank histogram. {histogram}.",
            f"- Every reason maps to a signal key. {'Yes' if valid else 'No'}.",
            f"- Recall@5 reaches 75%. {'Yes' if overall >= 0.75 else 'No'}.",
        ]
    return "\n".join(
        lines
        + extras
        + [
            "",
            "We designed these records. They show that the ranking logic works on this fixture and do not measure ZIPNET accuracy.",
            "",
            "Gnani requests 0. Ollama requests 0.",
            "",
        ]
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    content = report()
    if args.output:
        args.output.write_text(content, encoding="utf-8")
    else:
        print(content, end="")


if __name__ == "__main__":
    main()
