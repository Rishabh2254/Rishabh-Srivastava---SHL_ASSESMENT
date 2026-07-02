"""Find catalog API endpoints in SHL page source."""
import re
import requests

url = "https://www.shl.com/solutions/products/product-catalog/?type=1&start=0"
r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
text = r.text

patterns = [
    r"product-catalog[^\"'\s]{0,80}",
    r"catalogue[^\"'\s]{0,80}",
    r"/api/[^\"'\s]+",
    r"fetch\([^)]+\)",
    r"XMLHttpRequest[^;]{0,200}",
    r"type=1[^\"'\s]{0,40}",
    r"start=\d+",
]

for pat in patterns:
    matches = list(set(re.findall(pat, text, re.I)))
    if matches:
        print(f"\n=== {pat} ({len(matches)}) ===")
        for m in sorted(matches)[:20]:
            print(m[:120])

# Search for table-related class names
for cls in ["catalogue", "product-catalogue", "ss-catalog", "product-catalog"]:
    count = text.lower().count(cls.lower())
    if count:
        print(f"class {cls}: {count}")

# Look for JSON-LD or application/json
if "application/ld+json" in text:
    print("has json-ld")

# Try content hub / AEM servlet patterns common on enterprise sites
candidates = [
    "https://www.shl.com/solutions/products/product-catalog/jcr:content.json",
    "https://www.shl.com/bin/shl/productcatalog.json?type=1&start=0",
    "https://www.shl.com/content/shl/en/solutions/products/product-catalog/jcr:content.json",
]
for c in candidates:
    try:
        rr = requests.get(c, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        print(c, rr.status_code, rr.headers.get("content-type", "")[:40], rr.text[:100])
    except Exception as e:
        print(c, e)
