"""Deterministic keyword matching. No LLM: scores come from code, reasons from the same code."""

import re
from datetime import datetime

from .models import Filters, Hit, Record
from .parse import get_detail

STOP = {
    "a",
    "an",
    "the",
    "and",
    "or",
    "of",
    "in",
    "on",
    "at",
    "with",
    "is",
    "was",
    "has",
    "have",
    "he",
    "she",
    "his",
    "her",
    "about",
    "around",
    "years",
    "year",
    "old",
    "wearing",
    "wears",
    "last",
    "seen",
    "near",
    "speaks",
    "speak",
    "who",
    "that",
    "to",
    "from",
    "very",
    "some",
}
SYN = {  # Hinglish and common variants -> canonical English token
    "lal": "red",
    "laal": "red",
    "neela": "blue",
    "nila": "blue",
    "hara": "green",
    "peela": "yellow",
    "safed": "white",
    "kala": "black",
    "kaala": "black",
    "gulabi": "pink",
    "bhura": "brown",
    "ladka": "male",
    "boy": "male",
    "man": "male",
    "ladki": "female",
    "girl": "female",
    "woman": "female",
    "nishan": "mark",
    "kameez": "shirt",
    "kamiz": "shirt",
    "pants": "trouser",
    "pant": "trouser",
    "trousers": "trouser",
    "jeans": "trouser",
    "mole": "mark",
}


def _stem(t: str) -> str:
    return t[:-1] if len(t) > 3 and t.endswith("s") and not t.endswith("ss") else t


def tokens(s: str) -> list[str]:
    raw = re.findall(r"[a-z0-9\u0900-\u097f]+", (s or "").lower())
    out = []
    for t in raw:
        if t in STOP or len(t) < 2:
            continue
        t = SYN.get(t, t)
        t = _stem(t)
        out.append(SYN.get(t, t))
    return out


def _fields(r: Record) -> list[tuple[str, str, float]]:
    f = [
        ("place", r.place, 1.0),
        ("police station", r.police_station, 1.0),
        ("district", r.district, 1.0),
        ("state", r.state, 0.5),
    ]
    if r.details:
        f += [(k, v, 1.5) for k, v in r.details.items()]
    elif r.detail_text:
        f.append(("details", r.detail_text, 1.5))
    return f


def _int(s: str) -> int | None:
    m = re.search(r"\d+", s or "")
    return int(m.group()) if m else None


def passes(r: Record, f: Filters) -> bool:
    """Hard filters. Unknown values are wildcards, never exclusions."""
    g = get_detail(r, "sex", "gender")
    if f.gender and g and g.strip().lower()[0] != f.gender.strip().lower()[0]:
        return False
    age = _int(get_detail(r, "age"))
    if age is not None:
        if f.age_min is not None and age < f.age_min - 2:
            return False
        if f.age_max is not None and age > f.age_max + 2:
            return False
    return True


def _d(s: str) -> datetime | None:
    try:
        return datetime.strptime(s.strip(), "%d/%m/%Y")
    except Exception:
        return None


def local_filter(records: list[Record], f: Filters) -> list[Record]:
    out = []
    lo, hi = _d(f.date_from or ""), _d(f.date_to or "")
    for r in records:
        if f.status and r.status and r.status.strip().lower() != f.status.strip().lower():
            continue
        if f.state and r.state and r.state.strip().lower() != f.state.strip().lower():
            continue
        if f.district and r.district and f.district.strip().lower() not in r.district.lower():
            continue
        dd = _d(r.dd_date)
        if dd and ((lo and dd < lo) or (hi and dd > hi)):
            continue
        out.append(r)
    return out


def band(score: float) -> str:
    return "Strong" if score >= 0.6 else "Possible" if score >= 0.35 else "Weak"


def rank(records: list[Record], query: str, f: Filters, limit: int = 10) -> list[Hit]:
    q = list(dict.fromkeys(tokens(query)))
    pool = [r for r in local_filter(records, f) if passes(r, f)]
    if not q:
        pool.sort(key=lambda r: _d(r.reported_on) or datetime.min, reverse=True)
        return [Hit(record=r, score=0.0, band="Listed", reasons=[]) for r in pool[:limit]]
    hits = []
    for r in pool:
        fields = [(lab, set(tokens(txt)), w) for lab, txt, w in _fields(r)]
        credit, reasons = 0.0, []
        for t in q:
            best = max(((w, lab) for lab, ts, w in fields if t in ts), default=None)
            if best:
                credit += best[0]
                reasons.append(f"“{t}” found in {best[1].lower()}")
        score = credit / (1.5 * len(q))
        if score > 0:
            hits.append(
                Hit(record=r, score=round(min(score, 1.0), 3), band=band(score), reasons=reasons)
            )
    hits.sort(key=lambda h: h.score, reverse=True)
    return hits[:limit]
