"""Deep Playwright inspection of SHL catalog page."""
from playwright.sync_api import sync_playwright

url = "https://www.shl.com/solutions/products/product-catalog/?type=1&start=0"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto(url, wait_until="domcontentloaded", timeout=60000)

    # Dismiss cookie banner if present
    for sel in [
        "button:has-text('Accept')",
        "button:has-text('Accept All')",
        "#onetrust-accept-btn-handler",
        ".ot-sdk-container button",
    ]:
        btn = page.query_selector(sel)
        if btn:
            btn.click()
            page.wait_for_timeout(1000)
            break

    page.wait_for_timeout(5000)
    print("title:", page.title())
    print("url:", page.url)

    # Screenshot for debug
    page.screenshot(path=r"d:\SHL - Assesment\scripts\catalog_screenshot.png", full_page=True)

    # Check for iframes
    frames = page.frames
    print("frames:", len(frames))
    for i, frame in enumerate(frames):
        print(f"frame {i}:", frame.url[:100])
        tables = frame.query_selector_all("table")
        if tables:
            print(f"  tables in frame {i}:", len(tables))

    # All text containing OPQ or Verify
    body = page.inner_text("body")
    for kw in ["OPQ", "Verify", "catalog", "Individual", "Product", "Assessment"]:
        if kw.lower() in body.lower():
            print(f"body contains: {kw}")

    # Find all links
    all_links = page.eval_on_selector_all(
        "a[href]",
        "els => els.map(e => ({href: e.href, text: e.innerText.trim().slice(0,60)})).filter(x => x.text)",
    )
    product_links = [l for l in all_links if "view" in l["href"] or "product-catalog" in l["href"]]
    print("product links:", len(product_links))
    for l in product_links[:15]:
        print(l)

    # Check shadow DOM / custom elements
    html_snippet = page.content()
    for marker in ["catalogue", "product-catalogue", "ss-product", "data-start", "Individual Test"]:
        idx = html_snippet.lower().find(marker.lower())
        print(f"{marker}: {'found at ' + str(idx) if idx >= 0 else 'not found'}")

    browser.close()
