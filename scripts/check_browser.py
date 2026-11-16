"""Check the standalone viewer with Playwright, without a server or remote resources.

Run: uv sync --group browser; uv run playwright install chromium
     uv run python scripts/check_browser.py
"""

import json
from pathlib import Path

from playwright.sync_api import sync_playwright

root = Path(__file__).resolve().parents[1]
with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1000, "height": 900})
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    # A saved lesson should remain fully usable without any remote origin.
    page.route("https://**/*", lambda route: route.abort())
    page.route("http://**/*", lambda route: route.abort())
    page.goto((root / "output/elephant-walkthrough/index.html").as_uri())
    assert page.locator(".step-controls button").count() == 6
    page.get_by_role("button", name="2 Markdown", exact=True).click()
    assert "ELEPHANT FIELD NOTES" in page.locator("#elephant-content").inner_text()
    page.get_by_role("button", name="3 Normalized", exact=True).click()
    assert "ELEPHANT FIELD NOTES" not in page.locator("#elephant-content pre").first.inner_text()
    page.get_by_role("button", name="4 Chunks", exact=True).click()
    page.locator("#elephant-chunk").select_option("6")
    assert "starts inside a word" in page.locator("#elephant-content").inner_text()
    page.get_by_role("button", name="5 Embeddings", exact=True).click()
    page.get_by_text("All 384 embedding values", exact=False).click()
    assert "384 numbers" in page.locator("#elephant-content").inner_text()
    page.get_by_role("button", name="6 Retrieval", exact=True).click()
    page.locator("#elephant-question").select_option("3")
    assert "T06" in page.locator(".result summary").first.inner_text()
    assert page.locator(".result").count() == 7
    page.locator("#elephant-config").select_option("1")
    assert page.locator(".result").count() == 3
    page.set_viewport_size({"width": 360, "height": 800})
    page.get_by_role("button", name="4 Chunks", exact=True).click()
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    qa = root / "tmp" / "verification"
    qa.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(qa / "mobile-viewer.png"), full_page=True)
    assert not errors, errors
    browser.close()
print(json.dumps({"stage_buttons": 6, "offline": True, "mobile_overflow": False, "errors": errors}))
