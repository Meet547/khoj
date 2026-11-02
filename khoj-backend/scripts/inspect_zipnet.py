"""Run this FIRST on your machine:  python scripts/inspect_zipnet.py
It opens ZIPNET, lists the filter controls it can see, applies a PUNJAB filter, and records every
background request (URL, method, body, first 400 chars of response) into fixtures/discovery.json.
Send me that file and I can replace the browser with a direct, fast request.
"""

import asyncio
import json
import pathlib
import re
import sys

from playwright.async_api import async_playwright

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from app.crawler import LABEL_JS, UA, URL

OUT = pathlib.Path(__file__).resolve().parents[1] / "fixtures"


async def main():
    calls = []
    async with async_playwright() as pw:
        b = await pw.chromium.launch(headless="--headless" in sys.argv)
        page = await (await b.new_context(user_agent=UA)).new_page()

        async def on_resp(r):
            if r.request.resource_type in ("xhr", "fetch"):
                try:
                    body = (await r.text())[:400]
                except Exception:
                    body = ""
                calls.append(
                    {
                        "url": r.url,
                        "method": r.request.method,
                        "post": r.request.post_data,
                        "status": r.status,
                        "response_head": body,
                    }
                )

        page.on("response", on_resp)
        await page.goto(URL, wait_until="networkidle")
        await page.get_by_role("button", name=re.compile("Filter", re.I)).first.click()
        await page.wait_for_timeout(800)
        print("\nVisible controls in filter panel:")
        for sel in ("select:visible", "input:visible"):
            loc = page.locator(sel)
            for i in range(await loc.count()):
                el = loc.nth(i)
                print(
                    f"  {sel.split(':')[0]:7} label={await el.evaluate(LABEL_JS)!r:32} "
                    f"id={await el.get_attribute('id')!r} name={await el.get_attribute('name')!r}"
                )
        # Status is now first in the live DOM; select the observed State control.
        sel = page.locator("#ddlState")
        await page.wait_for_function(
            "[...document.querySelectorAll('#ddlState option')].some(o => /PUNJAB/i.test(o.textContent))"
        )
        opts = await sel.locator("option").evaluate_all(
            "os => os.map(o => [o.value, o.textContent.trim()])"
        )
        pick = next((o for o in opts if "PUNJAB" in o[1].upper()), None)
        if pick:
            await sel.select_option(value=pick[0])
        await page.get_by_role("button", name=re.compile(r"^\s*Apply\s*$", re.I)).first.click()
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(2000)
        await page.locator("table tbody tr td").first.click()  # open one "+" detail row
        await page.wait_for_timeout(2000)
        OUT.mkdir(exist_ok=True)
        (OUT / "discovery.json").write_text(json.dumps(calls, indent=2))
        (OUT / "table.html").write_text(await page.content())
        await page.screenshot(path=str(OUT / "after_filter.png"), full_page=True)
        print(
            f"\nSaved {len(calls)} background calls to fixtures/discovery.json (+ table.html, after_filter.png)"
        )
        await b.close()


asyncio.run(main())
