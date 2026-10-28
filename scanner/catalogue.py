"""
How big is this brand's catalogue, and how many images does a product carry?

Those two numbers are the whole euro model: photography is priced per image, so
`SKUs x images_per_SKU` is the volume Modelia would be quoting against.

Two ways to learn them, in order of preference:

  1. Shopify's /products.json — public on most stores, exact, one request per 250
     products, and it hands back the image list per product for free.
  2. XML sitemaps — every other platform. Counts product URLs, and reads
     <image:image> entries where the sitemap carries them.

Where a number is estimated rather than counted, `method` says so, and the report
prints it. A CEO checking one row must not find a figure we implied was exact.
"""
import random
import re
from urllib.parse import urljoin, urlparse
from xml.etree import ElementTree

MAX_PRODUCT_PAGES = 8          # 8 x 250 = 2000 products, then we extrapolate
PAGE_SIZE         = 250
MAX_SITEMAPS      = 12

NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9",
      "image": "http://www.google.com/schemas/sitemap-image/1.1"}

PRODUCT_URL_RX = re.compile(r"/(products?|producto|produkt|prodotto|p|item|shop)/", re.I)
PRODUCT_MAP_RX = re.compile(r"(product|producto|produkt|prodotto|catalog)", re.I)

# Plenty of stores put products at /es-es/oversize-layered-shirt with no marker
# segment at all. A product slug is long and hyphenated; a category is one word.
SLUG_RX   = re.compile(r"/[^/]*(?:-[^/]*){3,}/?$")
LOCALE_RX = re.compile(r"^/[a-z]{2}(?:[-_][a-z]{2})?(?=/)", re.I)
NOT_PRODUCT_RX = re.compile(
    r"/(blog|news|journal|pages?|collections?|categor|magazine|lookbook|stores?|"
    r"help|faq|legal|privacy|terms|account|search|gift|blogs)/", re.I)
MAX_PLAUSIBLE_SKUS = 60_000


class Catalogue:
    def __init__(self, skus, images_per_sku, samples, method, exact=True, notes=""):
        self.skus           = skus
        self.images_per_sku = images_per_sku
        self.samples        = samples      # [{title, url, image}]
        self.method         = method
        self.exact          = exact
        self.notes          = notes

    def __repr__(self):
        return (f"<Catalogue {self.skus} SKUs x {self.images_per_sku:.1f} img "
                f"via {self.method}>")


# ---------------------------------------------------------------- Shopify
def shopify(fetcher, base, sample_n=8):
    products, pages_read, hit_cap = [], 0, False

    for page in range(1, MAX_PRODUCT_PAGES + 1):
        url = urljoin(base, f"/products.json?limit={PAGE_SIZE}&page={page}")
        data = fetcher.json(url)
        if not data or "products" not in data:
            break
        batch = data["products"]
        products.extend(batch)
        pages_read += 1
        if len(batch) < PAGE_SIZE:
            break
        if page == MAX_PRODUCT_PAGES:
            hit_cap = True

    if not products:
        return None

    counted = len(products)
    img_counts = [len(p.get("images") or []) for p in products]
    images_per_sku = sum(img_counts) / max(counted, 1)

    skus, exact, notes = counted, True, ""
    if hit_cap:
        # We stopped early to stay polite. Ask the sitemap how many there really are.
        total = _sitemap_product_count(fetcher, base)
        if total and total > counted:
            skus, exact = total, False
            notes = (f"{counted} products read directly; catalogue total {total} from "
                     f"sitemap, images/SKU extrapolated from the sample")

    samples = _sample_shopify(products, sample_n, base)
    return Catalogue(skus, images_per_sku, samples,
                     f"shopify /products.json ({pages_read} page"
                     f"{'s' if pages_read != 1 else ''})", exact, notes)


def _sample_shopify(products, n, base):
    """Spread the sample across the catalogue. The first page of a Shopify store is
    usually newest-first, and a brand's newest products are often its best shot —
    sampling only those would flatter every brand we look at."""
    with_images = [p for p in products if (p.get("images") or [])]
    if not with_images:
        return []
    rng = random.Random(1)                       # deterministic: same list every run
    picked = (with_images if len(with_images) <= n
              else [with_images[round(i * (len(with_images) - 1) / (n - 1))]
                    for i in range(n)])
    if len(with_images) > n:                     # jitter off the exact stride
        pool = [p for p in with_images if p not in picked]
        if pool:
            picked[len(picked) // 2] = rng.choice(pool)

    out = []
    for p in picked:
        img = (p.get("images") or [{}])[0].get("src")
        if not img:
            continue
        out.append({"title": p.get("title", ""),
                    "url": urljoin(base, f"/products/{p.get('handle','')}"),
                    "image": img})
    return out


# ---------------------------------------------------------------- sitemaps
def _sitemap_urls(fetcher, base):
    """robots.txt is the polite place to ask where the sitemaps are."""
    found = []
    robots = fetcher.text(urljoin(base, "/robots.txt"))
    if robots:
        found += re.findall(r"(?im)^\s*sitemap:\s*(\S+)", robots)
    if not found:
        found = [urljoin(base, "/sitemap.xml"), urljoin(base, "/sitemap_index.xml")]
    return found[:4]


def _parse_xml(fetcher, url):
    body = fetcher.get(url)
    if not body or body["status"] != 200:
        return None
    raw = body["content"]
    if raw[:2] == b"\x1f\x8b":                    # gzipped sitemap
        import gzip
        try:
            raw = gzip.decompress(raw)
        except OSError:
            return None
    try:
        return ElementTree.fromstring(raw)
    except ElementTree.ParseError:
        return None


def _walk_sitemaps(fetcher, base):
    """-> list of (url_element_count, [url elements]) for product-looking sitemaps."""
    queue, seen, leaves = _sitemap_urls(fetcher, base), set(), []

    while queue and len(seen) < MAX_SITEMAPS:
        url = queue.pop(0)
        if url in seen:
            continue
        seen.add(url)
        root = _parse_xml(fetcher, url)
        if root is None:
            continue

        children = root.findall("sm:sitemap/sm:loc", NS)
        if children:                                   # a sitemap index
            kids = [c.text.strip() for c in children if c.text]
            product_kids = [k for k in kids if PRODUCT_MAP_RX.search(k)]
            queue.extend(product_kids or kids[:MAX_SITEMAPS])
            continue

        entries = root.findall("sm:url", NS)
        if entries:
            leaves.append((url, entries))
    return leaves


def _sitemap_product_count(fetcher, base):
    found = []
    for url, entries in _walk_sitemaps(fetcher, base):
        by_name = bool(PRODUCT_MAP_RX.search(url))
        for e in entries:
            loc = e.find("sm:loc", NS)
            if loc is None or not loc.text:
                continue
            t = loc.text.strip()
            if urlparse(t).path.rstrip("/") in ("", "/"):
                continue
            if by_name or _looks_like_product(t):
                found.append(t)
    found, _ = _one_locale(found)
    n = len({_dedupe_key(u) for u in found})
    return n if 0 < n <= MAX_PLAUSIBLE_SKUS else None


def sitemap(fetcher, base, sample_n=8):
    leaves = _walk_sitemaps(fetcher, base)
    if not leaves:
        return None

    product_entries, seen = [], set()
    for url, entries in leaves:
        by_name = bool(PRODUCT_MAP_RX.search(url))
        for e in entries:
            loc = e.find("sm:loc", NS)
            if loc is None or not loc.text:
                continue
            target = loc.text.strip()
            if urlparse(target).path.rstrip("/") in ("", "/"):
                continue
            if not (by_name or _looks_like_product(target)):
                continue
            key = _dedupe_key(target)
            if key in seen:
                continue
            seen.add(key)
            product_entries.append((target, e))

    if not product_entries:
        return None
    kept, locale_note = _one_locale([u for u, _ in product_entries])
    kept_set = set(kept)
    product_entries = [e for u, e in product_entries if u in kept_set]
    if not product_entries:
        return None
    if len(product_entries) > MAX_PLAUSIBLE_SKUS:
        # Almost certainly counting something that is not a product. Better to
        # report nothing than a number nobody can defend.
        return None

    # <image:image> is optional but common on fashion sitemaps, and when it is there
    # it gives images-per-SKU without fetching a single product page.
    img_counts = [len(e.findall("image:image", NS)) for e in product_entries]
    have_images = [c for c in img_counts if c]
    if have_images:
        images_per_sku = sum(have_images) / len(have_images)
        notes = f"images/SKU from <image:image> on {len(have_images)} sitemap entries"
        exact = True
    else:
        images_per_sku = 0.0                      # filled in by the sampler downstream
        notes = "sitemap carries no image entries; images/SKU sampled from product pages"
        exact = False

    rng = random.Random(1)
    picks = (product_entries if len(product_entries) <= sample_n
             else rng.sample(product_entries, sample_n))
    samples = []
    for e in picks:
        loc = e.find("sm:loc", NS).text.strip()
        img = e.find("image:image/image:loc", NS)
        samples.append({"title": _title_from_url(loc), "url": loc,
                        "image": img.text.strip() if img is not None and img.text else None})

    if locale_note:
        notes = f"{notes}; {locale_note}" if notes else locale_note
        exact = False

    return Catalogue(len(product_entries), images_per_sku, samples,
                     f"sitemap ({len(leaves)} file{'s' if len(leaves) != 1 else ''})",
                     exact, notes)


def _looks_like_product(url):
    path = urlparse(url).path
    if NOT_PRODUCT_RX.search(path):
        return False
    return bool(PRODUCT_URL_RX.search(path) or SLUG_RX.search(path))


def _dedupe_key(url):
    """Same product under /es-es/, /en-gb/ and /fr-fr/ is one product, not three."""
    path = urlparse(url).path.rstrip("/")
    return LOCALE_RX.sub("", path) or path


def _locale_of(url):
    m = LOCALE_RX.match(urlparse(url).path)
    return m.group(0).lower() if m else ""


def _one_locale(urls):
    """Count one language, not all of them.

    Stripping the locale prefix is not enough on a site that *translates* its slugs:
    Bimba y Lola publish the same shirt as /be_en/white-fitted-chili-top-... and
    /es_es/top-blanco-..., which share no key at all. Summing those gave 15,329 SKUs
    for a brand with roughly a tenth of that, and a six-figure saving built on it.

    So group by locale prefix and keep the biggest group. One language's catalogue is
    the catalogue; the rest are translations of it."""
    groups = {}
    for u in urls:
        groups.setdefault(_locale_of(u), []).append(u)
    if len(groups) <= 1:
        return urls, None
    best = max(groups, key=lambda k: len(groups[k]))
    return groups[best], f"{len(groups)} locales published; counted {best or '/'} only"


def _title_from_url(url):
    slug = urlparse(url).path.rstrip("/").split("/")[-1]
    return re.sub(r"[-_]+", " ", slug).strip().title()[:70]


# ---------------------------------------------------------------- entry
def size(fetcher, base, platform, sample_n=8):
    """Shopify's /products.json is one cheap request and exact, so it is worth
    trying even when detection was not sure — Scalpers runs Shopify but their
    homepage advertises a WordPress blog loudly enough to win the vote."""
    if platform in ("shopify", "unknown", "wordpress"):
        got = shopify(fetcher, base, sample_n)
        if got:
            return got
    return sitemap(fetcher, base, sample_n)
