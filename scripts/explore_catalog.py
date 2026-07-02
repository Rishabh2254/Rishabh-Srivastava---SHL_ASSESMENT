"""Temporary script to explore SHL catalog HTML structure."""
import re
import requests
from bs4 import BeautifulSoup

url = "https://www.shl.com/solutions/products/product-catalog/?type=1&start=0"
r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
text = r.text
soup = BeautifulSoup(text, "lxml")

print("status", r.status_code, "len", len(text))

# Tables and rows
for sel in ["table", "tbody tr", ".ss-table tr", "[data-product]", ".product", "li"]:
    els = soup.select(sel)
    if els:
        print(f"{sel}: {len(els)}")

# All links with view or catalog
links = []
for a in soup.find_all("a", href=True):
    href = a["href"]
    if "view" in href or "product-catalog" in href:
        links.append((href, a.get_text(strip=True)[:80]))
print("relevant links", len(links))
for h, t in links[:15]:
    print(" ", h[:90], "|", t)

# Script content search
for i, script in enumerate(soup.find_all("script")):
    content = script.string or ""
    if "product" in content.lower() and len(content) > 100:
        print(f"script {i} len={len(content)}")
        if "catalog" in content.lower() or "start" in content.lower():
            print(content[:500])

# Try paginated fragment
for start in [0, 12, 24]:
    u = f"https://www.shl.com/solutions/products/product-catalog/?type=1&start={start}"
    rr = requests.get(u, headers={"User-Agent": "Mozilla/5.0", "X-Requested-With": "XMLHttpRequest"}, timeout=30)
    ss = BeautifulSoup(rr.text, "lxml")
    trs = ss.select("tr")
    print(f"start={start} trs={len(trs)}")
    if trs:
        print(trs[0].get_text(" | ", strip=True)[:200])
