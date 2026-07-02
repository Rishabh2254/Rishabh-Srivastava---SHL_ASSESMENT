"""Playwright-based catalog probe."""
from playwright.sync_api import sync_playwright

url = "https://www.shl.com/solutions/products/product-catalog/?type=1&start=0"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto(url, wait_until="networkidle", timeout=60000)
    page.wait_for_timeout(3000)

    table = page.query_selector("table")
    print("table found:", table is not None)

    rows = page.query_selector_all("table tr")
    print("rows:", len(rows))
    for row in rows[:5]:
        print(row.inner_text()[:200])

    links = page.eval_on_selector_all(
        "table a[href]",
        "els => els.map(e => ({href: e.href, text: e.innerText.trim()}))",
    )
    print("table links:", len(links))
    for item in links[:8]:
        print(item)

    browser.close()
