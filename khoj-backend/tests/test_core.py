from app.models import Filters
from app.parse import parse_details, row_to_record
from app.search import rank, tokens

H = [
    "",
    "",
    "State",
    "District",
    "Police Station",
    "FIR Number",
    "DD Date",
    "Serial Number",
    "Place of Missing From",
    "Tracing Status",
    "Report Date on ZIPNET",
    "",
]


def mk(place, details_text, status="Untraced", state="PUNJAB"):
    cells = [
        "+",
        "",
        state,
        "PATIALA",
        "CIVIL LINES",
        "",
        "27/05/2013",
        "58/13",
        place,
        status,
        "27/06/2013",
        "",
    ]
    r = row_to_record(H, cells, "https://x/img.jpg")
    r.details, r.detail_text = parse_details(details_text)
    return r


def test_tokens_hinglish():
    t = tokens("Ladka lal kameez, scar on chin")
    assert {"male", "red", "shirt", "scar", "chin"} <= set(t)


def test_row_mapping_and_id():
    r = mk("HOME", "")
    assert r.state == "PUNJAB" and r.fir_no == "" and r.place == "HOME" and len(r.source_id) == 16


def test_pii_dropped():
    d, txt = parse_details(
        "Sex: Male\nComplainant's Phone: 9812345678\nGuardian Name: X Y\nDress Upper: Red shirt"
    )
    assert (
        "Sex" in d
        and "Dress Upper" in d
        and len(d) == 2
        and "9812345678" not in txt
        and "Guardian" not in txt
    )


def test_rank_bands_and_filters():
    a = mk(
        "HOME", "Sex: Male\nAge: 9\nDress Upper: Red shirt\nPhysical Details: Scar on left eyebrow"
    )
    b = mk("HOME", "Sex: Female\nAge: 9\nDress Upper: Red shirt")
    c = mk("Market", "Sex: Male\nAge: 40\nDress Upper: Grey coat")
    hits = rank(
        [a, b, c],
        "boy 9 years red shirt scar eyebrow",
        Filters(gender="male", age_min=7, age_max=11),
    )
    assert len(hits) == 1 and hits[0].band == "Strong" and any("scar" in x for x in hits[0].reasons)


def test_status_filter_and_browse_mode():
    a = mk("HOME", "Sex: Male")
    t = mk("HOME2", "Sex: Male", status="Traced")
    hits = rank([a, t], "", Filters(status="Untraced"))
    assert len(hits) == 1 and hits[0].band == "Listed"
