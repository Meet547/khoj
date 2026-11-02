"""The tool the harness will call later: search_zipnet(query, filters) -> ranked hits."""

import asyncio
import os
import time
from datetime import UTC, datetime
from typing import Any

from .cache import Cache
from .crawler import crawl
from .models import Filters, Record
from .search import rank

TTL = int(os.getenv("KHOJ_TTL", "21600"))
cache = Cache(os.getenv("KHOJ_DB", "khoj.db"), TTL)
_lock = asyncio.Lock()  # one crawl at a time: be gentle with a government server

DISCLAIMER = (
    "Bands show how strongly the written description matches a police record. "
    "They are not confirmation of identity. A person reviews every match before anyone is contacted."
)


async def search_zipnet(
    query: str,
    filters: Filters,
    refresh: bool = False,
    max_rows: int = 120,
    expand: bool = True,
    limit: int = 10,
) -> dict[str, Any]:
    if not filters.state:
        raise ValueError("Choose a state first.")
    key = f"{filters.crawl_key()}#{max_rows}#{int(expand)}"
    cached = cache.get(key)
    source, note = "cache", None
    if cached and not refresh and time.time() - cached[1] < TTL:
        recs, ts = [Record(**d) for d in cached[0]], cached[1]
    else:
        try:
            async with _lock:
                recs = await asyncio.wait_for(crawl(filters, max_rows, expand), timeout=240)
            cache.put(key, [r.model_dump() for r in recs])
            source, ts = "live", time.time()
        except Exception as e:
            if not cached:
                raise
            recs, ts = [Record(**d) for d in cached[0]], cached[1]
            source, note = (
                "stale-cache",
                f"Live check failed ({type(e).__name__}); showing older results.",
            )
    hits = rank(recs, query, filters, limit)
    return {
        "source": source,
        "checked_at": datetime.fromtimestamp(ts, UTC).isoformat(),
        "scanned": len(recs),
        "hits": [h.model_dump() for h in hits],
        "note": note,
        "disclaimer": DISCLAIMER,
    }
