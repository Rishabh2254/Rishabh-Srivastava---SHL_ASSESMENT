"""Search SHL catalog page for load mechanisms."""
import re
import requests
from bs4 import BeautifulSoup

url = "https://www.shl.com/solutions/products/product-catalog/?type=1&start=0"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}
r = requests.get(url, headers=headers, timeout=30)
text = r.text
soup = BeautifulSoup(text, "html.parser")

# SilverStripe patterns
for pat in [r"/solutions/products/product-catalog[^\"'\s]*", r"SilverStripe[^\"'\s]{0,60}", r"ajax[^\"'\s]{0,80}", r"loadCatalog[^\"'\s]{0,40}"]:
    found = sorted(set(re.findall(pat, text, re.I)))
    if found:
        print(pat, "=>", found[:15])

# data attributes
for tag in soup.find_all(attrs={"data-start": True}):
    print("data-start tag", tag.name, tag.attrs)
for tag in soup.find_all(class_=re.compile("catalog", re.I)):
    print("catalog class", tag.name, tag.get("class"), tag.get_text(" ", strip=True)[:100])

# Try POST to same URL
r2 = requests.post(url, headers={**headers, "X-Requested-With": "XMLHttpRequest"}, timeout=30)
print("POST status", r2.status_code, "has table", "<table" in r2.text.lower())

# Try catalog without type filter
for u in [
    "https://www.shl.com/solutions/products/product-catalog/",
    "https://www.shl.com/solutions/products/product-catalog/?start=0",
]:
    rr = requests.get(u, headers=headers, timeout=30)
    has_table = "<table" in rr.text.lower()
    tr_count = rr.text.lower().count("<tr")
    print(u, "table", has_table, "tr", tr_count)

# Test a known view URL
view = "https://www.shl.com/solutions/products/product-catalog/view/java-8-programming/"
rr = requests.get(view, headers=headers, timeout=30)
print("view page", rr.status_code, len(rr.text))
vsoup = BeautifulSoup(rr.text, "html.parser")
title = vsoup.find("h1")
print("h1", title.get_text(strip=True) if title else None)
for sec in vsoup.select(".product-detail__section, .ss-product-detail, article p")[:3]:
    print("sec", sec.get_text(" ", strip=True)[:150])
