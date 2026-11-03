"""Build fictional matching records in memory without reading external data."""

from dataclasses import dataclass
from datetime import date, timedelta
from random import Random

SEED = 20261103
CORE_DISTRACTORS = 100
TOTAL_DISTRACTORS = 150


@dataclass(frozen=True)
class Report:
    item_id: str
    kind: str
    fields: dict[str, str]


@dataclass(frozen=True)
class TruePair:
    missing_id: str
    found_id: str
    noise: str


def make_fields(
    rng: Random, serial: int, state: str, event: date, *, found: bool
) -> dict[str, str]:
    name = f"Velq{chr(97 + serial // 26)}{chr(97 + serial % 26)} Dovren"
    return {
        "state": state,
        "district": f"Orbel District {serial % 5 + 1}",
        "police_station": f"Tallowfen Station {serial % 7 + 1}",
        "fir_no": "" if found else f"FICTION-{serial:03}",
        "dd_date": event.isoformat(),
        "place_of_missing": f"Vellumwhorl Arcade {serial % 12 + 1}",
        "status": "Traced" if found else "Untraced",
        "report_date": (event + timedelta(days=2 if found else 1)).isoformat(),
        "sex": rng.choice(("female", "male")),
        "age": str(rng.randint(12, 85)),
        "height": str(rng.randint(135, 194)),
        "build": rng.choice(("slim", "medium", "stocky")),
        "complexion": rng.choice(("light", "medium", "dark")),
        "hair": rng.choice(("short black", "long black", "short brown", "grey")),
        "upper_dress": rng.choice(("blue coat", "grey shirt", "green vest", "striped sweater")),
        "lower_dress": rng.choice(("black trousers", "grey jeans", "brown shorts", "blue jeans")),
        "physical_details": "; ".join(
            (
                rng.choice(
                    ("left wrist scar", "chin dimple", "right elbow scar", "neck birthmark")
                ),
                rng.choice(
                    ("left knee scar", "right ankle mark", "freckled cheek", "split eyebrow")
                ),
            )
        ),
        "description": f"Name reported as {name}. Fictional exercise report.",
    }


def add_noise(fields: dict[str, str], changes: list[str]) -> None:
    for change in changes:
        if change == "date":
            shifted = date.fromisoformat(fields["dd_date"]) + timedelta(days=9)
            fields["dd_date"] = shifted.isoformat()
            fields["report_date"] = (shifted + timedelta(days=2)).isoformat()
        elif change == "station":
            fields["police_station"] = "Brambleweft Annex Station"
        elif change == "name":
            fields["description"] = fields["description"].replace("Dovren", "Dovarn")
        elif change == "age":
            age = int(fields["age"])
            fields["age"] = f"{age - 2}-{age + 3}"
        elif change == "mark":
            fields["physical_details"] = fields["physical_details"].split("; ")[0]
        elif change == "clothing":
            fields["upper_dress"] = "maroon pullover"
            fields["lower_dress"] = "tan trousers"


def generate() -> tuple[list[Report], list[Report], list[Report], list[TruePair]]:
    rng = Random(SEED)
    missing, found, distractors, truth = [], [], [], []
    noise_options = ("date", "station", "name", "age", "mark", "clothing")
    for i in range(50):
        state = f"Fablemark State {i % 5 + 1}"
        event = date(2026, 2, 1) + timedelta(days=rng.randrange(120))
        original = make_fields(rng, i, state, event, found=False)
        counterpart = {
            **original,
            "status": "Traced",
            "fir_no": "",
            "report_date": (event + timedelta(days=2)).isoformat(),
        }
        count = (0, 1, 2 + i % 5)[i % 3]
        add_noise(counterpart, rng.sample(noise_options, count))
        left, right = f"M-{i + 1:03}", f"F-{i + 1:03}"
        missing.append(Report(left, "missing", original))
        found.append(Report(right, "found", counterpart))
        truth.append(TruePair(left, right, ("none", "one", "two or more")[min(count, 2)]))

    shared_fields = ("age", "height", "physical_details", "upper_dress", "hair", "place_of_missing")
    for i in range(TOTAL_DISTRACTORS):
        anchor = missing[i % len(missing)].fields
        serial = 50 + i
        event = date(2026, 2, 1) + timedelta(days=rng.randrange(120))
        fields = make_fields(rng, serial, anchor["state"], event, found=True)
        copied = rng.sample(shared_fields, 1 + i % 2)
        for key in shared_fields:
            if key in copied:
                fields[key] = anchor[key]
            elif fields[key] == anchor[key]:
                # Prevent accidental exact matches among the controlled overlap fields.
                fields[key] = {
                    "age": "86",
                    "height": "195",
                    "physical_details": "right thumb scar",
                    "upper_dress": "beige parka",
                    "hair": "shaved",
                    "place_of_missing": "Fablethread Courtyard",
                }[key]
        assert sum(fields[key] == anchor[key] for key in shared_fields) == len(copied)
        distractors.append(Report(f"D-{i + 1:03}", "found", fields))
    return missing, found, distractors, truth
