"""ZIPNET missing-persons crawler (Playwright).

Drives the real page like a person would: open Filter, pick state/district/status, Apply,
read the DataTable page by page, click "+" to read each row's detail panel.
Reads columns by header text, so a column reorder does not break it.
If a control can't be found, it raises CrawlError telling you to run scripts/inspect_zipnet.py.
"""

import asyncio
import os
import re
from typing import cast
from urllib.robotparser import RobotFileParser

from playwright.async_api import Locator, Page, async_playwright

from .models import Filters, Record
from .parse import parse_details, row_to_record
from .search import local_filter

BASE = "https://zipnet.delhipolice.gov.in"
URL = BASE + "/Victims/MissingPersons"
UA = f"KHOJ-Crawler/0.1 (non-profit missing-persons search; contact: {os.getenv('KHOJ_CONTACT', 'set-KHOJ_CONTACT')})"
DELAY_MS = int(float(os.getenv("KHOJ_DELAY", "1.0")) * 1000)


class CrawlError(Exception):
    pass


def robots_allows() -> bool:
    rp = RobotFileParser(BASE + "/robots.txt")
    try:
        rp.read()
    except Exception:
        return True  # robots.txt unreachable: proceed politely
    return rp.can_fetch(UA, URL)


# Label of a form control = <label for>, wrapping label, text next to a radio/checkbox, or nearby text.
LABEL_JS = r"""el => {
  let t = '';
  if (el.id) { const l = document.querySelector('label[for="' + el.id + '"]'); if (l) t = l.innerText; }
  if (!t) { const l = el.closest('label'); if (l) t = l.innerText; }
  if (!t && (el.type === 'radio' || el.type === 'checkbox')) {
    t = (el.nextSibling && el.nextSibling.textContent) || (el.parentElement ? el.parentElement.innerText : '');
  }
  if (!t) { let p = el.previousElementSibling; while (p && !t) { t = p.innerText || ''; p = p.previousElementSibling; } }
  if (!t && el.parentElement && el.parentElement.previousElementSibling) t = el.parentElement.previousElementSibling.innerText || '';
  if (!t) t = el.getAttribute('aria-label') || el.name || el.id || '';
  return t.replace(/\s+/g, ' ').replace(/:/g, '').trim();
}"""

READ_JS = r"""() => {
  const tables = [...document.querySelectorAll('table')];
  const ht = tables.find(t => t.tHead && /FIR/i.test(t.tHead.innerText) && /Police/i.test(t.tHead.innerText));
  if (!ht) return null;
  const headers = [...ht.tHead.querySelectorAll('th')].map(h => h.innerText.replace(/\s+/g, ' ').trim());
  const body = (ht.tBodies[0] && ht.tBodies[0].rows.length) ? ht
    : tables.find(x => x.tBodies[0] && x.tBodies[0].rows.length && x.tBodies[0].rows[0].cells.length === headers.length);
  if (!body) return {headers, rows: []};
  const rows = [...body.tBodies[0].rows].filter(r => r.cells.length >= headers.length - 2);
  rows.forEach((r, i) => r.dataset.khojIdx = String(i));
  return {headers, rows: rows.map(r => ({cells: [...r.cells].map(c => c.innerText), img: (r.querySelector('img') || {}).src || null}))};
}"""

NEXT_ROW_JS = """e => { const n = e.nextElementSibling;
  if (!n || n.dataset.khojIdx !== undefined) return ''; return n.innerText || ''; }"""


async def _controls(page: Page, css: str) -> list[tuple[str, Locator]]:
    loc = page.locator(css)
    return [
        ((await loc.nth(i).evaluate(LABEL_JS)).lower(), loc.nth(i))
        for i in range(await loc.count())
    ]


async def _select(page: Page, key: str, wanted: str) -> None:
    el = next((e for lab, e in await _controls(page, "select:visible") if key in lab), None)
    if el is None:
        raise CrawlError(
            f"Dropdown '{key}' not found in filter panel. Run scripts/inspect_zipnet.py."
        )
    opts = []
    for _ in range(40):  # dependent dropdowns (district) fill via AJAX
        opts = await el.locator("option").evaluate_all(
            "os => os.map(o => [o.value, o.textContent.trim()])"
        )
        if len(opts) > 1:
            break
        await page.wait_for_timeout(250)
    w = wanted.strip().lower()
    pick = next((o for o in opts if o[1].lower() == w), None) or next(
        (o for o in opts if w in o[1].lower()), None
    )
    if not pick:
        raise CrawlError(f"'{wanted}' not in '{key}' list: {[o[1] for o in opts[:10]]}")
    await el.select_option(value=pick[0])


async def _status(page: Page, status: str) -> bool:
    for lab, el in await _controls(page, "input[type=radio]:visible, input[type=checkbox]:visible"):
        if lab == status.strip().lower():  # exact: "traced" is inside "untraced"
            await el.check()
            return True
    return False  # local filter still enforces status


async def _read_page(page: Page, expand: bool, seen: set[str], budget: int) -> list[Record]:
    data = await page.evaluate(READ_JS)
    if not data:
        raise CrawlError("Results table not found. Run scripts/inspect_zipnet.py.")
    out: list[Record] = []
    for i, row in enumerate(data["rows"]):
        if len(out) >= budget:
            break
        rec = row_to_record(data["headers"], row["cells"], row["img"])
        if not rec or rec.source_id in seen:
            continue
        if expand:
            text = await _expand(page, i)
            rec.details, rec.detail_text = parse_details(text)
        seen.add(rec.source_id)
        out.append(rec)
    return out


async def _expand(page: Page, idx: int) -> str:
    row = page.locator(f'tr[data-khoj-idx="{idx}"]')
    try:
        await row.locator("td").first.click(timeout=3000)
        for _ in range(12):
            txt = await row.evaluate(NEXT_ROW_JS)
            if txt.strip():
                return cast(str, txt)
            await page.wait_for_timeout(250)
    except Exception:
        pass
    return ""


async def _next_page(page: Page) -> bool:
    nxt = page.locator("li.paginate_button.next a, a.paginate_button.next").first
    if not await nxt.count():
        return False
    cls = await nxt.evaluate(
        "e => e.className + ' ' + (e.parentElement ? e.parentElement.className : '')"
    )
    if "disabled" in cls:
        return False
    await nxt.click()
    await page.wait_for_timeout(DELAY_MS + 500)
    return True


async def crawl(f: Filters, max_rows: int = 120, expand: bool = True) -> list[Record]:
    if not await asyncio.to_thread(robots_allows):
        raise CrawlError("robots.txt disallows crawling this path.")
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        try:
            page = await (await browser.new_context(user_agent=UA, locale="en-IN")).new_page()
            page.set_default_timeout(20000)
            await page.goto(URL, wait_until="networkidle")
            await page.get_by_role("button", name=re.compile("Filter", re.I)).first.click()
            await page.wait_for_timeout(500)
            if f.state:
                await _select(page, "state", f.state)
            if f.district:
                await _select(page, "district", f.district)
            if f.police_station:
                await _select(page, "police station", f.police_station)
            if f.status:
                await _status(page, f.status)
            await page.get_by_role("button", name=re.compile(r"^\s*Apply\s*$", re.I)).first.click()
            await page.wait_for_load_state("networkidle")
            await page.wait_for_timeout(DELAY_MS)

            size = page.locator("select[name$='_length']")  # "Show N entries": take the largest
            if await size.count():
                vals = await size.first.locator("option").evaluate_all("os => os.map(o => o.value)")
                nums = [v for v in vals if v.lstrip("-").isdigit() and int(v) > 0]
                if nums:
                    await size.first.select_option(value=max(nums, key=int))
                    await page.wait_for_timeout(DELAY_MS + 500)

            records: list[Record] = []
            seen: set[str] = set()
            while len(records) < max_rows:
                records += await _read_page(page, expand, seen, max_rows - len(records))
                if len(records) >= max_rows or not await _next_page(page):
                    break
            return local_filter(records, f)
        finally:
            await browser.close()
