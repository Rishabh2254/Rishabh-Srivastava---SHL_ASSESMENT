"""Extract product catalog URLs from SHL sitemap."""
import re
import requests

SITEMAP = "https://www.shl.com/sitemap.xml/sitemap/SilverStripe-CMS-Model-SiteTree/1?l=en_US"
r = requests.get(SITEMAP, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
urls = re.findall(r"<loc>([^<]+)</loc>", r.text)
catalog = [u for u in urls if "product-catalog/view" in u]
print("total urls", len(urls), "catalog view", len(catalog))
for u in catalog[:10]:
    print(u)

# Also check page 2 and 3
for page in [2, 3]:
    sm = f"https://www.shl.com/sitemap.xml/sitemap/SilverStripe-CMS-Model-SiteTree/{page}?l=en_US"
    rr = requests.get(sm, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
    uu = re.findall(r"<loc>([^<]+)</loc>", rr.text)
    cat = [u for u in uu if "product-catalog/view" in u]
    print(f"page {page}: total {len(uu)}, catalog {len(cat)}")
