import hashlib
import re

from .models import Record

HEADER_MAP = {
    "state": "state",
    "district": "district",
    "police station": "police_station",
    "fir number": "fir_no",
    "dd date": "dd_date",
    "serial number": "serial_no",
    "place of missing from": "place",
    "tracing status": "status",
    "report date on zipnet": "reported_on",
}
# Family / complainant contact data is never stored: KHOJ doesn't need it to match.
PII_HINTS = (
    "phone",
    "mobile",
    "contact",
    "address",
    "complainant",
    "guardian",
    "report information",
    "occupation",
)


def _clean(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def is_pii(key: str) -> bool:
    k = key.lower()
    return any(h in k for h in PII_HINTS)


def row_to_record(headers: list[str], cells: list[str], img: str | None) -> Record | None:
    d: dict[str, str] = {}
    for h, c in zip(headers, cells, strict=False):
        k = HEADER_MAP.get(_clean(h).lower())
        if k:
            d[k] = _clean(c)
    if not (d.get("state") or d.get("district")):
        return None
    ident = "|".join(
        d.get(k, "")
        for k in ("state", "district", "police_station", "fir_no", "dd_date", "serial_no", "place")
    )
    sid = hashlib.sha1(ident.encode()).hexdigest()[:16]
    if img and ("image_not_available" in img or img.endswith("/")):
        img = None
    return Record(source_id=sid, image_url=img, **d)


def parse_details(text: str) -> tuple[dict[str, str], str]:
    """Return (key/value details, scrubbed text). Lines that look like PII are dropped."""
    details, keep = {}, []
    for line in (text or "").splitlines():
        line = _clean(line)
        if not line:
            continue
        m = re.match(r"^([A-Za-z][A-Za-z /().&'-]{1,40}?)\s*:\s*(.+)$", line)
        if m:
            if is_pii(m.group(1)):
                continue
            details[m.group(1).strip()] = m.group(2).strip()
        elif is_pii(line):
            continue
        keep.append(line)
    return details, "\n".join(keep)


def get_detail(rec: Record, *names: str) -> str:
    for k, v in rec.details.items():
        if any(n in k.lower() for n in names):
            return v
    return ""
