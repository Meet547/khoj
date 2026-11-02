from datetime import UTC, datetime

from pydantic import BaseModel, Field


class Filters(BaseModel):
    # Sent to the ZIPNET filter panel (server-side)
    state: str | None = None
    district: str | None = None
    police_station: str | None = None
    status: str | None = "Untraced"  # Untraced | Traced | None
    # Applied locally after the crawl (cheap, and safe if the portal form changes)
    date_from: str | None = None  # dd/mm/yyyy, compared with DD date
    date_to: str | None = None
    gender: str | None = None  # male | female | other
    age_min: int | None = None
    age_max: int | None = None

    def crawl_key(self) -> str:
        return "|".join(
            (x or "").strip().lower()
            for x in (self.state, self.district, self.police_station, self.status)
        )


class Record(BaseModel):
    source: str = "zipnet"
    source_id: str
    state: str = ""
    district: str = ""
    police_station: str = ""
    fir_no: str = ""
    dd_date: str = ""
    serial_no: str = ""
    place: str = ""
    status: str = ""
    reported_on: str = ""
    image_url: str | None = None
    details: dict[str, str] = Field(default_factory=dict)  # parsed from the "+" row
    detail_text: str = ""  # PII-scrubbed raw text
    fetched_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


class Hit(BaseModel):
    record: Record
    score: float
    band: str  # Strong | Possible | Weak | Listed
    reasons: list[str]
